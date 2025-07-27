import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from pathlib import Path
from typing import List, Dict, Any, Optional
from pdf_objects import extract_pdf_objects_from_bytes

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

class PDFViewer:
    def __init__(self, pdf_path: Path):
        self.root = tk.Tk()  # Create root window first
        self.pdf_path = pdf_path
        self.current_page = 0
        self.scale_factor = 1.0
        self.show_bboxes = tk.BooleanVar(self.root)  # Pass root as master
        self.hovered_obj = None
        self.objects: List[Dict[str, Any]] = extract_pdf_objects_from_bytes(pdf_path.read_bytes())
        self.pages = sorted(set(obj['page'] for obj in self.objects))
        self.total_pages = len(self.pages)
        self.page_height = self._get_page_height()
        self.tk_img = None  # Hold reference to the current page image
        self.setup_gui()
        self.load_page(0)

    def _get_page_height(self) -> float:
        # Try to get page height from PyMuPDF or fallback
        if HAS_PYMUPDF:
            doc = fitz.open(str(self.pdf_path))
            return doc[0].rect.height
        # Fallback: use max bbox height
        return max(obj['bbox'][3] for obj in self.objects if obj['type'] in ['word', 'text_line', 'rect', 'table', 'graphic_line', 'curve', 'image'])

    def setup_gui(self):
        self.root.title(f"PDF Viewer - {Path(self.pdf_path).name}")
        self.root.geometry("1400x900")
        self.show_bboxes.set(True)
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="Previous", command=self.prev_page).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Next", command=self.next_page).pack(side=tk.LEFT, padx=2)
        self.page_label = ttk.Label(toolbar, text="")
        self.page_label.pack(side=tk.LEFT, padx=10)
        ttk.Label(toolbar, text="Zoom:").pack(side=tk.LEFT, padx=(20, 2))
        ttk.Button(toolbar, text="-", command=self.zoom_out).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="+", command=self.zoom_in).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="Fit", command=self.zoom_fit).pack(side=tk.LEFT, padx=2)
        bbox_check = ttk.Checkbutton(toolbar, text="Show Bounding Boxes", variable=self.show_bboxes, command=self.toggle_bboxes)
        bbox_check.pack(side=tk.LEFT, padx=(20, 2))
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        viewer_frame = ttk.Frame(paned)
        paned.add(viewer_frame, weight=3)
        canvas_frame = ttk.Frame(viewer_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_mouse_motion)
        details_frame = ttk.Frame(paned)
        paned.add(details_frame, weight=1)
        ttk.Label(details_frame, text="Object Details", font=('TkDefaultFont', 12, 'bold')).pack(pady=5)
        self.details_text = scrolledtext.ScrolledText(details_frame, height=20, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.status_var = tk.StringVar()
        self.status_var.set("Click on objects to see details")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def load_page(self, page_num: int):
        if page_num < 0 or page_num >= self.total_pages:
            return
        self.current_page = page_num
        self.page_label.config(text=f"Page {page_num + 1} of {self.total_pages}")
        self.page_height = self._get_page_height()
        self.page_objects = [obj for obj in self.objects if obj['page'] == self.pages[page_num]]
        self.canvas.delete("all")

        # Render PDF page as image if possible
        if HAS_PYMUPDF and HAS_PIL:
            doc = fitz.open(str(self.pdf_path))
            page = doc[self.pages[page_num]]
            mat = fitz.Matrix(self.scale_factor, self.scale_factor)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
            self.canvas.config(scrollregion=(0, 0, img.width, img.height))

        if self.show_bboxes.get():
            self.draw_bounding_boxes()

    def draw_bounding_boxes(self, highlight_obj=None):
        colors = {
            'word': '#ADD8E6',
            'text_line': '#90EE90',
            'table': '#FFB6C1',
            'rect': '#FFA07A',
            'curve': '#DDA0DD',
            'graphic_line': '#B0C4DE',
            'image': '#FFD700',
        }
        highlight_colors = {
            'word': '#4682B4',
            'text_line': '#228B22',
            'table': '#C71585',
            'rect': '#CD5C5C',
            'curve': '#8B008B',
            'graphic_line': '#4682B4',
            'image': '#FF8C00',
        }
        max_x, max_y = 0, 0
        for obj in self.page_objects:
            x0, y0, x1, y1 = obj['bbox']
            if HAS_PYMUPDF and HAS_PIL and self.scale_factor != 1.0:
                canvas_x0 = x0 * self.scale_factor
                canvas_x1 = x1 * self.scale_factor
                canvas_y0 = (self.page_height - y1) * self.scale_factor
                canvas_y1 = (self.page_height - y0) * self.scale_factor
            else:
                canvas_x0, canvas_x1 = x0, x1
                canvas_y0 = self.page_height - y1
                canvas_y1 = self.page_height - y0
            if highlight_obj is not None and obj is highlight_obj:
                fill = highlight_colors.get(obj['type'], '#555555')
                outline = '#000000'
                width = 3
                stipple = ''
            else:
                fill = colors.get(obj['type'], '#D3D3D3')
                outline = fill
                width = 1
                stipple = 'gray25'
            rect_id = self.canvas.create_rectangle(
                canvas_x0, canvas_y0, canvas_x1, canvas_y1,
                fill=fill, outline=outline, width=width,
                stipple=stipple,
                tags=f"bbox_{obj['type']}"
            )
            obj['canvas_id'] = rect_id
            max_x = max(max_x, canvas_x1)
            max_y = max(max_y, canvas_y1)
        if not HAS_PYMUPDF or not HAS_PIL:
            self.canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def toggle_bboxes(self):
        if self.show_bboxes.get():
            self.draw_bounding_boxes()
        else:
            self.canvas.delete("bbox_word", "bbox_text_line", "bbox_table", "bbox_rect", "bbox_curve", "bbox_graphic_line", "bbox_image")

    def on_canvas_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        if HAS_PYMUPDF and HAS_PIL and self.scale_factor != 1.0:
            pdf_x = canvas_x / self.scale_factor
            pdf_y = canvas_y / self.scale_factor
            pdf_y = self.page_height - pdf_y
        else:
            pdf_x = canvas_x
            pdf_y = self.page_height - canvas_y
        clicked = None
        for obj in self.page_objects:
            x0, y0, x1, y1 = obj['bbox']
            if x0 <= pdf_x <= x1 and y0 <= pdf_y <= y1:
                clicked = obj
                break
        if clicked:
            self.show_object_details(clicked)
            self.status_var.set(f"Clicked on {clicked['type']}: {clicked.get('text', str(clicked.get('type')))}")
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
        hovered = None
        for obj in self.page_objects:
            x0, y0, x1, y1 = obj['bbox']
            if x0 <= pdf_x <= x1 and y0 <= pdf_y <= y1:
                hovered = obj
                break
        if hovered is not self.hovered_obj:
            self.hovered_obj = hovered
            self.canvas.delete("bbox_word", "bbox_text_line", "bbox_table", "bbox_rect", "bbox_curve", "bbox_graphic_line", "bbox_image")
            self.draw_bounding_boxes(highlight_obj=hovered)

    def show_object_details(self, obj: Dict[str, Any]):
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, f"Object Type: {obj['type'].upper()}\n", "bold")
        if 'text' in obj:
            self.details_text.insert(tk.END, f"Content: {obj['text']}\n\n")
        self.details_text.insert(tk.END, "Bounding Box:\n", "bold")
        x0, y0, x1, y1 = obj['bbox']
        self.details_text.insert(tk.END, f"  x0: {x0:.1f}\n")
        self.details_text.insert(tk.END, f"  y0: {y0:.1f}\n")
        self.details_text.insert(tk.END, f"  x1: {x1:.1f}\n")
        self.details_text.insert(tk.END, f"  y1: {y1:.1f}\n")
        self.details_text.insert(tk.END, f"  Width: {x1 - x0:.1f}\n")
        self.details_text.insert(tk.END, f"  Height: {y1 - y0:.1f}\n\n")
        self.details_text.insert(tk.END, "Additional Details:\n", "bold")
        for key, value in obj.items():
            if key not in ['bbox', 'text', 'type', 'page', 'canvas_id']:
                self.details_text.insert(tk.END, f"  {key}: {value}\n")
        self.details_text.tag_configure("bold", font=('TkDefaultFont', 10, 'bold'))

    def prev_page(self):
        if self.current_page > 0:
            self.load_page(self.current_page - 1)

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.load_page(self.current_page + 1)

    def zoom_in(self):
        self.scale_factor *= 1.2
        self.load_page(self.current_page)

    def zoom_out(self):
        self.scale_factor /= 1.2
        self.load_page(self.current_page)

    def zoom_fit(self):
        self.scale_factor = 1.0
        self.load_page(self.current_page)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a PDF file to analyze",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
    )
    if not file_path:
        root.destroy()
        exit(0)
    root.destroy()
    viewer = PDFViewer(Path(file_path))
    viewer.run() 