"""
pdf_analyzer.py
Opens a file-picker, lets you choose a file, then:
1. Checks if it's a valid PDF
2. If valid, displays the PDF in an interactive viewer
3. Allows clicking on text objects and shapes to see their details
4. Also provides console analysis of all text objects and tables

Dependencies: pdfplumber, PIL (Pillow), pymupdf (fitz)
"""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pdfplumber
import sys
from typing import List, Dict, Any, Tuple, Optional

# Try to import PDF rendering libraries
try:
    import fitz  # PyMuPDF  # type: ignore
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def safe_print(text: str, encoding='utf-8', errors='replace') -> None:
    """Safely print text handling encoding issues."""
    try:
        # Try to encode/decode to handle Unicode issues
        if isinstance(text, str):
            # Replace problematic characters with safe alternatives
            safe_text = text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
            print(safe_text)
        else:
            print(str(text))
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback: replace all non-ASCII characters
        safe_text = ''.join(char if ord(char) < 128 else '?' for char in str(text))
        print(safe_text)


def safe_str(obj) -> str:
    """Safely convert object to string, handling encoding issues."""
    try:
        text = str(obj) if obj is not None else "None"
        # Replace problematic characters
        return text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback: replace all non-ASCII characters
        return ''.join(char if ord(char) < 128 else '?' for char in str(obj) if obj is not None)


def is_pdf(path: Path) -> bool:
    """Return True iff `path` is an existing, readable PDF."""
    if not path.exists() or not path.is_file():
        return False

    try:
        with pdfplumber.open(str(path)):
            return True
    except Exception:  # includes pdfplumber.pdfparser.PDFSyntaxError
        return False


class PDFObject:
    """Represents a clickable PDF object with its bounding box and details."""
    
    def __init__(self, obj_type: str, bbox: Tuple[float, float, float, float], 
                 content: str, details: Dict[str, Any]):
        self.obj_type = obj_type  # 'word', 'line', 'table', 'rect', 'curve'
        self.bbox = bbox  # (x0, y0, x1, y1)
        self.content = content
        self.details = details
        self.canvas_id: Optional[int] = None  # For bounding box visualization
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point (x, y) is inside this object's bounding box."""
        x0, y0, x1, y1 = self.bbox
        return x0 <= x <= x1 and y0 <= y <= y1


class InteractivePDFViewer:
    """Interactive PDF viewer with clickable text objects and shapes."""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.current_page = 0
        self.pdf_objects: List[PDFObject] = []
        self.scale_factor = 1.0
        self.page_height = 792  # Default page height, will be updated
        
        # Initialize PDF document
        if HAS_PYMUPDF:
            self.pdf_doc = fitz.open(str(pdf_path))
        else:
            self.pdf_doc = None
            
        with pdfplumber.open(str(pdf_path)) as pdf:
            self.plumber_pdf = pdf
            self.total_pages = len(pdf.pages)
            self.page_data = {}  # Cache for extracted page data
            
        self.setup_gui()
        self.load_page(0)
    
    def setup_gui(self):
        """Set up the main GUI window."""
        self.root = tk.Tk()
        self.root.title(f"Interactive PDF Viewer - {self.pdf_path.name}")
        self.root.geometry("1400x900")
        
        # Initialize tkinter variables after root is created
        self.show_bboxes = tk.BooleanVar()
        self.hovered_obj = None  # Track currently hovered object
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation buttons
        ttk.Button(toolbar, text="Previous", command=self.prev_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Next", command=self.next_page).pack(side=tk.LEFT, padx=2)
        
        # Page info
        self.page_label = ttk.Label(toolbar, text="")
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        # Zoom controls
        ttk.Label(toolbar, text="Zoom:").pack(side=tk.LEFT, padx=(20, 2))
        ttk.Button(toolbar, text="-", command=self.zoom_out).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="+", command=self.zoom_in).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="Fit", command=self.zoom_fit).pack(side=tk.LEFT, padx=2)
        
        # Bounding box checkbox
        bbox_check = ttk.Checkbutton(toolbar, text="Show Bounding Boxes", 
                                   variable=self.show_bboxes, command=self.toggle_bboxes)
        bbox_check.pack(side=tk.LEFT, padx=(20, 2))
        
        # Analysis button
        ttk.Button(toolbar, text="Console Analysis", command=self.run_console_analysis).pack(side=tk.RIGHT, padx=2)
        
        # Create paned window for main content
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - PDF viewer
        viewer_frame = ttk.Frame(paned)
        paned.add(viewer_frame, weight=3)
        
        # Canvas with scrollbars for PDF display
        canvas_frame = ttk.Frame(viewer_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind mouse events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_mouse_motion)
        
        # Right panel - Object details
        details_frame = ttk.Frame(paned)
        paned.add(details_frame, weight=1)
        
        ttk.Label(details_frame, text="Object Details", font=('TkDefaultFont', 12, 'bold')).pack(pady=5)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, height=20, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Click on text objects or shapes to see details")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def extract_page_objects(self, page_num: int) -> List[PDFObject]:
        """Extract all clickable objects from a PDF page."""
        if page_num in self.page_data:
            return self.page_data[page_num]
        
        objects = []
        
        with pdfplumber.open(str(self.pdf_path)) as pdf:
            page = pdf.pages[page_num]
            self.page_height = page.height  # Store actual page height
            
            # Extract words (complete text objects) - more robust approach
            try:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                safe_print(f"Raw words extracted: {len(words)}")
                for i, word in enumerate(words):
                    # Handle different coordinate formats pdfplumber might return
                    x0 = word.get('x0')
                    x1 = word.get('x1') 
                    
                    # Handle coordinate system conversion
                    if 'y0' in word and 'y1' in word:
                        # Direct PDF coordinates (bottom-left origin)
                        y0 = word['y0']
                        y1 = word['y1']
                    elif 'top' in word and 'bottom' in word:
                        # Convert from top/bottom (top-left origin) to PDF coordinates (bottom-left origin)
                        y0 = page.height - word['bottom']  # bottom edge in PDF coordinates
                        y1 = page.height - word['top']     # top edge in PDF coordinates
                    else:
                        y0 = None
                        y1 = None
                    
                    if x0 is not None and x1 is not None and y0 is not None and y1 is not None:
                        bbox = (x0, y0, x1, y1)
                        content = safe_str(word.get('text', ''))
                        if content.strip():  # Only add non-empty words
                            # Debug first few words to see coordinate conversion
                            if i < 3:
                                if 'top' in word and 'bottom' in word:
                                    safe_print(f"Word '{content}': top={word['top']}, bottom={word['bottom']} -> y0={y0}, y1={y1} (page_height={page.height})")
                                else:
                                    safe_print(f"Word '{content}': direct coordinates y0={y0}, y1={y1}")
                            
                            details = {
                                'index': i,
                                'text': content,
                                'size': word.get('size', 'unknown'),
                                'fontname': safe_str(word.get('fontname', 'unknown')),
                                'position': bbox,
                                'width': x1 - x0,
                                'height': y1 - y0
                            }
                            objects.append(PDFObject('word', bbox, content, details))
                    else:
                        # Only show first few failures to avoid spam
                        if i < 5:
                            safe_print(f"Word {i} missing coordinates: {word.keys()}")
                
                # Show how many words were successfully processed
                word_count = len([obj for obj in objects if obj.obj_type == 'word'])
                safe_print(f"Successfully processed {word_count} words out of {len(words)}")
            except Exception as e:
                safe_print(f"Error extracting words: {e}")
                # Fallback: extract from characters if words fail
                try:
                    chars = page.chars
                    safe_print(f"Fallback: using characters ({len(chars)} found)")
                    # Group characters into words manually
                    current_word = []
                    current_bbox = None
                    word_index = 0
                    
                    for char in chars:
                        if 'text' in char and char['text'].strip():
                            if char['text'].isspace():
                                # End current word
                                if current_word:
                                    word_text = ''.join([c['text'] for c in current_word])
                                    if current_bbox:
                                        details = {
                                            'index': word_index,
                                            'text': word_text,
                                            'position': current_bbox,
                                            'width': current_bbox[2] - current_bbox[0],
                                            'height': current_bbox[3] - current_bbox[1],
                                            'chars_count': len(current_word)
                                        }
                                        objects.append(PDFObject('word', tuple(current_bbox), word_text, details))
                                        word_index += 1
                                # Reset for next word
                                current_word = []
                                current_bbox = None
                            else:
                                # Add to current word
                                current_word.append(char)
                                if current_bbox is None:
                                    current_bbox = [char['x0'], char['y0'], char['x1'], char['y1']]
                                else:
                                    # Expand bounding box
                                    current_bbox[0] = min(current_bbox[0], char['x0'])
                                    current_bbox[1] = min(current_bbox[1], char['y0'])
                                    current_bbox[2] = max(current_bbox[2], char['x1'])
                                    current_bbox[3] = max(current_bbox[3], char['y1'])
                    
                    # Don't forget the last word
                    if current_word and current_bbox:
                        word_text = ''.join([c['text'] for c in current_word])
                        details = {
                            'index': word_index,
                            'text': word_text,
                            'position': tuple(current_bbox),
                            'width': current_bbox[2] - current_bbox[0],
                            'height': current_bbox[3] - current_bbox[1],
                            'chars_count': len(current_word)
                        }
                        objects.append(PDFObject('word', tuple(current_bbox), word_text, details))
                        
                except Exception as e2:
                    safe_print(f"Character fallback also failed: {e2}")
            
            # Extract text lines (for larger text blocks) - more robust
            try:
                lines = page.extract_text_lines(layout=True)
                safe_print(f"Text lines extracted: {len(lines)}")
                for i, line in enumerate(lines):
                    # Handle different coordinate formats
                    x0 = line.get('x0')
                    x1 = line.get('x1')
                    
                    # Handle coordinate system conversion
                    if 'y0' in line and 'y1' in line:
                        # Direct PDF coordinates (bottom-left origin)
                        y0 = line['y0']
                        y1 = line['y1']
                    elif 'top' in line and 'bottom' in line:
                        # Convert from top/bottom (top-left origin) to PDF coordinates (bottom-left origin)
                        y0 = page.height - line['bottom']  # bottom edge in PDF coordinates
                        y1 = page.height - line['top']     # top edge in PDF coordinates
                    else:
                        y0 = None
                        y1 = None
                    
                    if x0 is not None and x1 is not None and y0 is not None and y1 is not None:
                        bbox = (x0, y0, x1, y1)
                        content = safe_str(line.get('text', ''))
                        if content.strip():  # Only add non-empty lines
                            details = {
                                'index': i,
                                'text': content,
                                'position': bbox,
                                'width': x1 - x0,
                                'height': y1 - y0,
                                'chars_count': len(content)
                            }
                            objects.append(PDFObject('line', bbox, content, details))
                    else:
                        # Only show first few failures to avoid spam
                        if i < 5:
                            safe_print(f"Line {i} missing coordinates: {line.keys()}")
                
                # Show how many lines were successfully processed
                line_count = len([obj for obj in objects if obj.obj_type == 'line'])
                safe_print(f"Successfully processed {line_count} text lines out of {len(lines)}")
            except Exception as e:
                safe_print(f"Error extracting text lines: {e}")
            
            # Extract rectangles and shapes
            try:
                # Extract rectangle objects
                rects = page.rects
                for i, rect in enumerate(rects):
                    bbox = (rect['x0'], rect['y0'], rect['x1'], rect['y1'])
                    content = f"Rectangle {i+1}"
                    # Debug first rectangle
                    if i == 0:
                        safe_print(f"Rectangle: x0={rect['x0']}, y0={rect['y0']}, x1={rect['x1']}, y1={rect['y1']}")
                    details = {
                        'index': i,
                        'type': 'rectangle',
                        'position': bbox,
                        'width': rect['x1'] - rect['x0'],
                        'height': rect['y1'] - rect['y0'],
                        'linewidth': rect.get('linewidth', 'unknown'),
                        'stroke': rect.get('stroke', 'unknown'),
                        'fill': rect.get('fill', 'unknown')
                    }
                    objects.append(PDFObject('rect', bbox, content, details))
                
                # Extract line objects
                lines_shapes = page.lines
                for i, line in enumerate(lines_shapes):
                    # Create a bounding box for the line
                    x0, y0 = min(line['x0'], line['x1']), min(line['y0'], line['y1'])
                    x1, y1 = max(line['x0'], line['x1']), max(line['y0'], line['y1'])
                    # Add some padding for easier clicking
                    padding = 2
                    bbox = (x0 - padding, y0 - padding, x1 + padding, y1 + padding)
                    content = f"Line {i+1}"
                    # Debug first line
                    if i == 0:
                        safe_print(f"Line: start=({line['x0']}, {line['y0']}), end=({line['x1']}, {line['y1']}) -> bbox={bbox}")
                    details = {
                        'index': i,
                        'type': 'line',
                        'start': (line['x0'], line['y0']),
                        'end': (line['x1'], line['y1']),
                        'position': bbox,
                        'linewidth': line.get('linewidth', 'unknown'),
                        'stroke': line.get('stroke', 'unknown')
                    }
                    objects.append(PDFObject('line', bbox, content, details))
                
                # Extract curve objects
                curves = page.curves
                for i, curve in enumerate(curves):
                    # Create bounding box from curve points
                    if 'pts' in curve and curve['pts']:
                        # Flip Y-coordinates for all points
                        flipped_pts = [(pt[0], page.height - pt[1]) for pt in curve['pts']]
                        x_coords = [pt[0] for pt in flipped_pts]
                        y_coords = [pt[1] for pt in flipped_pts]
                        x0, x1 = min(x_coords), max(x_coords)
                        y0, y1 = min(y_coords), max(y_coords)
                        bbox = (x0, y0, x1, y1)
                        content = f"Curve {i+1}"
                        # Debug first curve to check coordinate system
                        if i == 0:
                            safe_print(f"Curve: points={flipped_pts[:3]}... -> bbox=({x0}, {y0}, {x1}, {y1})")
                        details = {
                            'index': i,
                            'type': 'curve',
                            'points': flipped_pts,
                            'position': bbox,
                            'width': x1 - x0,
                            'height': y1 - y0,
                            'linewidth': curve.get('linewidth', 'unknown'),
                            'stroke': curve.get('stroke', 'unknown')
                        }
                        objects.append(PDFObject('curve', bbox, content, details))
                        
            except Exception as e:
                safe_print(f"Error extracting shapes: {e}")
            
            # Extract tables
            try:
                tables = page.extract_tables()
                for i, table in enumerate(tables):
                    if table:
                        # Try to get table bounding box from table settings
                        table_bbox = page.bbox  # Default fallback
                        
                        # Attempt to find table bounds from table cells
                        try:
                            table_finder = page.debug_tablefinder()
                            if hasattr(table_finder, 'tables') and table_finder.tables:
                                if i < len(table_finder.tables):
                                    table_obj = table_finder.tables[i]
                                    if hasattr(table_obj, 'bbox'):
                                        # Table bbox may be in top-left origin, so flip if needed
                                        tb = table_obj.bbox
                                        # If y0 > y1, it's likely top-left origin
                                        if tb[1] < tb[3]:
                                            # Flip y0 and y1
                                            y0_flipped = page.height - tb[3]
                                            y1_flipped = page.height - tb[1]
                                            table_bbox = (tb[0], y0_flipped, tb[2], y1_flipped)
                                        else:
                                            table_bbox = tb
                        except Exception as e:
                            safe_print(f"Table bbox fallback: {e}")
                            pass  # Use fallback
                        
                        content = f"Table {i+1} ({len(table)}x{len(table[0]) if table else 0})"
                        details = {
                            'index': i,
                            'type': 'table',
                            'rows': len(table),
                            'cols': len(table[0]) if table else 0,
                            'content': table[:3],  # Store first 3 rows for preview
                            'position': table_bbox,
                            'full_table': table
                        }
                        objects.append(PDFObject('table', table_bbox, content, details))
                        safe_print(f"Table {i+1} bbox: {table_bbox}")  # Debug table coordinates
            except Exception as e:
                safe_print(f"Error extracting tables: {e}")
        
        # Sort objects by size (smaller objects first for better click detection)
        objects.sort(key=lambda obj: (obj.bbox[2] - obj.bbox[0]) * (obj.bbox[3] - obj.bbox[1]))
        
        self.page_data[page_num] = objects
        return objects
    
    def render_page_image(self, page_num: int) -> Optional[Image.Image]:
        """Render PDF page as an image."""
        if not HAS_PYMUPDF or not self.pdf_doc:
            return None
        
        try:
            page = self.pdf_doc[page_num]
            mat = fitz.Matrix(self.scale_factor, self.scale_factor)
            pix = page.get_pixmap(matrix=mat)  # type: ignore
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data)) if HAS_PIL else None
            return img
        except Exception as e:
            safe_print(f"Error rendering page: {e}")
            return None
    
    def load_page(self, page_num: int):
        """Load and display a PDF page."""
        if page_num < 0 or page_num >= self.total_pages:
            return
        
        self.current_page = page_num
        self.page_label.config(text=f"Page {page_num + 1} of {self.total_pages}")
        
        # Extract objects for this page
        self.pdf_objects = self.extract_page_objects(page_num)
        
        # Print object counts by type
        obj_counts = {}
        for obj in self.pdf_objects:
            obj_counts[obj.obj_type] = obj_counts.get(obj.obj_type, 0) + 1
        
        safe_print(f"Page {page_num + 1} objects: {dict(obj_counts)}")
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Try to render page image
        if HAS_PYMUPDF and HAS_PIL:
            img = self.render_page_image(page_num)
            if img:
                self.photo = ImageTk.PhotoImage(img)
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                
                # Draw bounding boxes if enabled
                if hasattr(self, 'show_bboxes') and self.show_bboxes.get():
                    self.draw_bounding_boxes()
                return
        
        # Fallback: draw bounding boxes if no image rendering available
        self.draw_bounding_boxes()
    
    def draw_bounding_boxes(self, highlight_obj=None):
        """Draw bounding boxes for all objects. Optionally highlight one object."""
        colors = {
            'word': '#ADD8E6',     # Light blue
            'line': '#90EE90',     # Light green  
            'table': '#FFB6C1',    # Light pink
            'rect': '#FFA07A',     # Light salmon
            'curve': '#DDA0DD'     # Plum
        }
        highlight_colors = {
            'word': '#4682B4',     # Steel blue
            'line': '#228B22',     # Forest green
            'table': '#C71585',    # Medium violet red
            'rect': '#CD5C5C',     # Indian red
            'curve': '#8B008B'     # Dark magenta
        }
        
        max_x, max_y = 0, 0
        
        for obj in self.pdf_objects:
            x0, y0, x1, y1 = obj.bbox
            if HAS_PYMUPDF and HAS_PIL and self.scale_factor != 1.0:
                canvas_x0 = x0 * self.scale_factor
                canvas_x1 = x1 * self.scale_factor
                canvas_y0 = (self.page_height - y1) * self.scale_factor
                canvas_y1 = (self.page_height - y0) * self.scale_factor
            else:
                canvas_x0, canvas_x1 = x0, x1
                canvas_y0 = self.page_height - y1
                canvas_y1 = self.page_height - y0
            
            # Highlight if this is the hovered object
            if highlight_obj is not None and obj is highlight_obj:
                fill = highlight_colors.get(obj.obj_type, '#555555')
                outline = '#000000'
                width = 3
                stipple = ''
            else:
                fill = colors.get(obj.obj_type, '#D3D3D3')
                outline = fill
                width = 1
                stipple = 'gray25'
            
            rect_id = self.canvas.create_rectangle(
                canvas_x0, canvas_y0, canvas_x1, canvas_y1,
                fill=fill, outline=outline, width=width,
                stipple=stipple,
                tags=f"bbox_{obj.obj_type}"
            )
            obj.canvas_id = rect_id
            max_x = max(max_x, canvas_x1)
            max_y = max(max_y, canvas_y1)
        
        if not HAS_PYMUPDF or not HAS_PIL:
            self.canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def toggle_bboxes(self):
        """Toggle visibility of bounding boxes."""
        if hasattr(self, 'show_bboxes') and self.show_bboxes.get():
            # Show bounding boxes
            self.draw_bounding_boxes()
        else:
            # Hide bounding boxes
            self.canvas.delete("bbox_word", "bbox_line", "bbox_table", "bbox_rect", "bbox_curve")
    
    def on_canvas_click(self, event):
        """Handle mouse click on canvas."""
        # Get canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to PDF coordinates
        if HAS_PYMUPDF and HAS_PIL and self.scale_factor != 1.0:
            pdf_x = canvas_x / self.scale_factor
            pdf_y = canvas_y / self.scale_factor
            # Convert from top-left origin to bottom-left origin (PDF standard)
            pdf_y = self.page_height - pdf_y
        else:
            # Using bounding box display
            pdf_x = canvas_x
            pdf_y = self.page_height - canvas_y  # Convert back to PDF coordinates
        
        # Find clicked objects
        clicked_objects = []
        for obj in self.pdf_objects:
            if obj.contains_point(pdf_x, pdf_y):
                clicked_objects.append(obj)
        
        if clicked_objects:
            # Prioritize by object type preference: word > line > rect > curve > table
            type_priority = {'word': 0, 'line': 1, 'rect': 2, 'curve': 3, 'table': 4}
            clicked_objects.sort(key=lambda o: (
                type_priority.get(o.obj_type, 5),
                (o.bbox[2] - o.bbox[0]) * (o.bbox[3] - o.bbox[1])  # Then by size
            ))
            
            clicked_obj = clicked_objects[0]
            self.show_object_details(clicked_obj)
            self.status_var.set(f"Clicked on {clicked_obj.obj_type}: {clicked_obj.content[:50]}...")
        else:
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, "No object found at this location.\n\n")
            self.details_text.insert(tk.END, f"Click coordinates: ({pdf_x:.1f}, {pdf_y:.1f})")
            self.status_var.set(f"No object found at ({pdf_x:.1f}, {pdf_y:.1f})")
    
    def on_mouse_motion(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        if HAS_PYMUPDF and HAS_PIL and self.scale_factor != 1.0:
            pdf_x = canvas_x / self.scale_factor
            pdf_y = canvas_y / self.scale_factor
            pdf_y = self.page_height - pdf_y
        else:
            pdf_x = canvas_x
            pdf_y = self.page_height - canvas_y
        self.status_var.set(f"Mouse: ({pdf_x:.1f}, {pdf_y:.1f}) - Click on objects to see details")
        # Hover highlight logic
        hovered = None
        for obj in self.pdf_objects:
            if obj.contains_point(pdf_x, pdf_y):
                hovered = obj
                break
        if hovered is not self.hovered_obj:
            self.hovered_obj = hovered
            self.canvas.delete("bbox_word", "bbox_line", "bbox_table", "bbox_rect", "bbox_curve")
            self.draw_bounding_boxes(highlight_obj=hovered)
    
    def show_object_details(self, obj: PDFObject):
        """Display details of clicked object."""
        self.details_text.delete(1.0, tk.END)
        
        self.details_text.insert(tk.END, f"Object Type: {obj.obj_type.upper()}\n", "bold")
        self.details_text.insert(tk.END, f"Content: {obj.content}\n\n")
        
        self.details_text.insert(tk.END, "Bounding Box:\n", "bold")
        x0, y0, x1, y1 = obj.bbox
        self.details_text.insert(tk.END, f"  x0: {x0:.1f}\n")
        self.details_text.insert(tk.END, f"  y0: {y0:.1f}\n")
        self.details_text.insert(tk.END, f"  x1: {x1:.1f}\n")
        self.details_text.insert(tk.END, f"  y1: {y1:.1f}\n")
        self.details_text.insert(tk.END, f"  Width: {x1 - x0:.1f}\n")
        self.details_text.insert(tk.END, f"  Height: {y1 - y0:.1f}\n\n")
        
        self.details_text.insert(tk.END, "Additional Details:\n", "bold")
        for key, value in obj.details.items():
            if key not in ['position', 'content', 'full_table']:  # Skip already shown items
                if key == 'text' and len(str(value)) > 100:
                    # Truncate long text
                    self.details_text.insert(tk.END, f"  {key}: {str(value)[:100]}...\n")
                else:
                    self.details_text.insert(tk.END, f"  {key}: {value}\n")
        
        # Show table preview for table objects
        if obj.obj_type == 'table' and 'content' in obj.details:
            self.details_text.insert(tk.END, "\nTable Preview:\n", "bold")
            table_preview = obj.details['content']
            for i, row in enumerate(table_preview):
                row_str = " | ".join([str(cell)[:15] + "..." if cell and len(str(cell)) > 15 
                                    else str(cell) if cell else "None" for cell in row])
                self.details_text.insert(tk.END, f"  Row {i+1}: {row_str}\n")
        
        # Configure text tags for formatting
        self.details_text.tag_configure("bold", font=('TkDefaultFont', 10, 'bold'))
    
    def prev_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.load_page(self.current_page - 1)
    
    def next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages - 1:
            self.load_page(self.current_page + 1)
    
    def zoom_in(self):
        """Increase zoom level."""
        self.scale_factor *= 1.2
        self.load_page(self.current_page)
    
    def zoom_out(self):
        """Decrease zoom level."""
        self.scale_factor /= 1.2
        self.load_page(self.current_page)
    
    def zoom_fit(self):
        """Reset zoom to fit page."""
        self.scale_factor = 1.0
        self.load_page(self.current_page)
    
    def run_console_analysis(self):
        """Run the original console analysis."""
        extract_text_objects(self.pdf_path)
    
    def run(self):
        """Start the GUI event loop."""
        self.root.mainloop()
        if self.pdf_doc:
            self.pdf_doc.close()


# Import io for image handling
import io


def extract_text_objects(pdf_path: Path) -> None:
    """Extract and print all text objects from the PDF."""
    safe_print(f"\n{'='*60}")
    safe_print(f"ANALYZING PDF: {pdf_path.name}")
    safe_print(f"{'='*60}")
    
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            safe_print(f"Total pages: {len(pdf.pages)}\n")
            
            for page_num, page in enumerate(pdf.pages, 1):
                safe_print(f"\n{'─'*50}")
                safe_print(f"PAGE {page_num}")
                safe_print(f"{'─'*50}")
                safe_print(f"Page dimensions: {page.width:.1f} x {page.height:.1f}")
                
                # Extract different types of text objects
                extract_page_text_objects(page, page_num)
                
                # Extract tables
                extract_page_tables(page, page_num)
                
    except Exception as e:
        safe_print(f"Error analyzing PDF: {e}")


def extract_page_text_objects(page, page_num: int) -> None:
    """Extract various text objects from a single page."""
    
    # 1. Characters
    chars = page.chars
    safe_print(f"\n🔤 CHARACTERS ({len(chars)} found):")
    if chars:
        safe_print("Sample characters (first 10):")
        for i, char in enumerate(chars[:10]):
            char_text = safe_str(char.get('text', ''))
            fontname = safe_str(char.get('fontname', 'unknown'))
            size = char.get('size', 'unknown')
            safe_print(f"  [{i+1}] '{char_text}' at ({char['x0']:.1f}, {char['y0']:.1f}) "
                      f"font: {fontname} size: {size}")
        if len(chars) > 10:
            safe_print(f"  ... and {len(chars) - 10} more characters")
    else:
        safe_print("  No characters found")
    
    # 2. Words
    try:
        words = page.extract_words()
        safe_print(f"\n🔤 WORDS ({len(words)} found):")
        if words:
            safe_print("Sample words (first 15):")
            for i, word in enumerate(words[:15]):
                word_text = safe_str(word.get('text', ''))
                size = word.get('size', 'unknown')
                safe_print(f"  [{i+1}] '{word_text}' at ({word['x0']:.1f}, {word['y0']:.1f}) "
                          f"size: {size}")
            if len(words) > 15:
                safe_print(f"  ... and {len(words) - 15} more words")
        else:
            safe_print("  No words found")
    except Exception as e:
        safe_print(f"  Error extracting words: {e}")
    
    # 3. Text lines
    try:
        lines = page.extract_text_lines()
        safe_print(f"\n📝 TEXT LINES ({len(lines)} found):")
        if lines:
            for i, line in enumerate(lines[:20]):  # Show first 20 lines
                line_text = safe_str(line.get('text', ''))
                text_preview = line_text[:80] + "..." if len(line_text) > 80 else line_text
                safe_print(f"  [{i+1}] '{text_preview}'")
                safe_print(f"      Position: ({line['x0']:.1f}, {line['y0']:.1f}) to ({line['x1']:.1f}, {line['y1']:.1f})")
            if len(lines) > 20:
                safe_print(f"  ... and {len(lines) - 20} more lines")
        else:
            safe_print("  No text lines found")
    except Exception as e:
        safe_print(f"  Error extracting text lines: {e}")
    
    # 4. Full page text
    try:
        full_text = page.extract_text()
        if full_text:
            safe_full_text = safe_str(full_text)
            text_preview = safe_full_text.strip()[:200] + "..." if len(safe_full_text.strip()) > 200 else safe_full_text.strip()
            safe_print(f"\n📄 FULL PAGE TEXT (preview):")
            safe_print(f"  Total characters: {len(full_text)}")
            safe_print(f"  Preview: {repr(text_preview)}")
        else:
            safe_print(f"\n📄 FULL PAGE TEXT: No text found")
    except Exception as e:
        safe_print(f"\n📄 FULL PAGE TEXT: Error extracting text: {e}")


def extract_page_tables(page, page_num: int) -> None:
    """Extract and display tables from a single page."""
    
    try:
        tables = page.extract_tables()
        safe_print(f"\n📊 TABLES ({len(tables)} found):")
        
        if not tables:
            safe_print("  No tables found")
            return
        
        for i, table in enumerate(tables, 1):
            safe_print(f"\n  TABLE {i}:")
            safe_print(f"  Dimensions: {len(table)} rows x {len(table[0]) if table else 0} columns")
            
            if table:
                # Print table headers and first few rows
                safe_print("  Content preview:")
                for row_idx, row in enumerate(table[:5]):  # Show first 5 rows
                    safe_row = []
                    for cell in row:
                        cell_str = safe_str(cell)
                        if cell_str and len(cell_str) > 20:
                            safe_row.append(cell_str[:20] + "...")
                        else:
                            safe_row.append(cell_str if cell_str else "None")
                    
                    row_preview = " | ".join(safe_row)
                    safe_print(f"    Row {row_idx + 1}: {row_preview}")
                
                if len(table) > 5:
                    safe_print(f"    ... and {len(table) - 5} more rows")
            
            # Also try to get table with settings for better detection
            try:
                table_settings = {
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict"
                }
                
                detailed_tables = page.extract_tables(table_settings=table_settings)
                if detailed_tables and i <= len(detailed_tables):
                    detailed_table = detailed_tables[i-1]
                    if detailed_table != table:  # If different from simple extraction
                        safe_print(f"  \n  DETAILED TABLE {i} (with strict line detection):")
                        safe_print(f"  Dimensions: {len(detailed_table)} rows x {len(detailed_table[0]) if detailed_table else 0} columns")
            except Exception as e:
                safe_print(f"  Error with detailed table extraction: {e}")
                
    except Exception as e:
        safe_print(f"\n📊 TABLES: Error extracting tables: {e}")


def select_and_analyze_pdf() -> None:
    """Open file dialog, pick file, check if PDF, and launch interactive viewer."""
    # Set console encoding for better Unicode support on Windows
    if sys.platform.startswith('win'):
        try:
            # Try to set UTF-8 encoding for console output
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore
        except (AttributeError, OSError):
            # Fallback for older Python versions or restricted environments
            pass
    
    root = tk.Tk()
    root.withdraw()  # hide the root window

    file_path = filedialog.askopenfilename(
        title="Select a PDF file to analyze",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
    )

    if not file_path:  # user cancelled
        root.destroy()
        return

    pdf_path = Path(file_path)
    pdf_ok = is_pdf(pdf_path)
    
    safe_print(f"\nFile selected: {pdf_path.name}")
    safe_print(f"Is valid PDF: {pdf_ok}")
    
    if pdf_ok:
        root.destroy()  # Close file dialog root
        
        # Check dependencies
        if not HAS_PYMUPDF:
            safe_print("Warning: PyMuPDF not installed. PDF rendering will be limited.")
            safe_print("Install with: pip install pymupdf")
        
        if not HAS_PIL:
            safe_print("Warning: PIL/Pillow not installed. Image display will be limited.")
            safe_print("Install with: pip install pillow")
        
        # Launch interactive viewer
        safe_print("\nLaunching interactive PDF viewer...")
        viewer = InteractivePDFViewer(pdf_path)
        viewer.run()
        
    else:
        safe_print("Cannot analyze - file is not a valid PDF.")
        messagebox.showerror(
            title="Not a PDF",
            message=f"'{pdf_path.name}' is not a valid PDF file.",
        )
        root.destroy()


if __name__ == "__main__":
  try:
        select_and_analyze_pdf()
  except KeyboardInterrupt:
        safe_print("\nKeyboardInterrupt - Analysis stopped by user")
        exit(0)