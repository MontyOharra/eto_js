import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Configure PDF.js worker - use local worker from node_modules
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

// ===== NESTED PDF OBJECT INTERFACES =====

interface BasePdfObject {
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
}

interface TextWordPdfObject extends BasePdfObject {
  text: string;
  fontname: string;
  fontsize: number;
}

interface TextLinePdfObject extends BasePdfObject {
  // Only has base fields
}

interface GraphicRectPdfObject extends BasePdfObject {
  linewidth: number;
}

interface GraphicLinePdfObject extends BasePdfObject {
  linewidth: number;
}

interface GraphicCurvePdfObject extends BasePdfObject {
  points: number[][];
  linewidth: number;
}

interface ImagePdfObject extends BasePdfObject {
  format: string;
  colorspace: string;
  bits: number;
}

interface TablePdfObject extends BasePdfObject {
  rows: number;
  cols: number;
}

interface PdfObjectsByType {
  text_words: TextWordPdfObject[];
  text_lines: TextLinePdfObject[];
  graphic_rects: GraphicRectPdfObject[];
  graphic_lines: GraphicLinePdfObject[];
  graphic_curves: GraphicCurvePdfObject[];
  images: ImagePdfObject[];
  tables: TablePdfObject[];
}

interface ExtractionField {
  id: string;
  boundingBox: [number, number, number, number];
  page: number;
  label: string;
}

// ===== FLAT OBJECT TYPE FOR RENDERING =====

type FlatObjectType = 'word' | 'text_line' | 'rect' | 'graphic_line' | 'curve' | 'image' | 'table';

interface FlatPdfObject {
  type: FlatObjectType;
  page: number;
  bbox: [number, number, number, number];
  text?: string;
  fontname?: string;
  fontsize?: number;
  linewidth?: number;
  points?: number[][];
  format?: string;
  colorspace?: string;
  bits?: number;
  rows?: number;
  cols?: number;
}

// ===== COMPONENT PROPS =====

interface PdfViewerProps {
  pdfUrl?: string;
  pdfId?: number;
  pdfObjects?: PdfObjectsByType;
  className?: string;
  showObjectOverlays?: boolean;
  onObjectClick?: (object: FlatPdfObject) => void;
  onObjectDoubleClick?: (object: FlatPdfObject) => void;
  selectedObjectTypes?: Set<string>;
  selectedObjects?: Set<string>;
  extractionFields?: ExtractionField[];
  selectedExtractionField?: string | null;
  isReadOnly?: boolean;
  // Box drawing props
  isDrawingMode?: boolean;
  drawingBox?: {x: number, y: number, width: number, height: number} | null;
  tempFieldData?: {id: string, boundingBox: [number, number, number, number], page: number} | null;
  onMouseDown?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onMouseMove?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onMouseUp?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
}

// ===== STYLING CONSTANTS =====

const OBJECT_COLORS: Record<FlatObjectType, string> = {
  word: 'rgba(255, 0, 0, 0.2)',
  text_line: 'rgba(0, 255, 0, 0.2)',
  rect: 'rgba(0, 0, 255, 0.2)',
  graphic_line: 'rgba(255, 255, 0, 0.2)',
  curve: 'rgba(255, 0, 255, 0.2)',
  image: 'rgba(0, 255, 255, 0.2)',
  table: 'rgba(255, 165, 0, 0.3)'
};

const OBJECT_BORDER_COLORS: Record<FlatObjectType, string> = {
  word: 'rgba(255, 0, 0, 0.6)',
  text_line: 'rgba(0, 255, 0, 0.6)',
  rect: 'rgba(0, 0, 255, 0.6)',
  graphic_line: 'rgba(255, 255, 0, 0.6)',
  curve: 'rgba(255, 0, 255, 0.6)',
  image: 'rgba(0, 255, 255, 0.6)',
  table: 'rgba(255, 165, 0, 0.8)'
};

export function PdfViewer({
  pdfUrl,
  pdfId,
  pdfObjects,
  className = '',
  showObjectOverlays = true,
  onObjectClick,
  onObjectDoubleClick,
  selectedObjectTypes,
  selectedObjects,
  extractionFields = [],
  selectedExtractionField,
  isReadOnly = false,
  isDrawingMode = false,
  drawingBox = null,
  tempFieldData = null,
  onMouseDown,
  onMouseMove,
  onMouseUp
}: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pageHeight, setPageHeight] = useState<number>(792); // Default Letter height
  const [pageWidth, setPageWidth] = useState<number>(612); // Default Letter width
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<{ [key: number]: HTMLDivElement }>({});

  // Determine the PDF URL to use
  const effectivePdfUrl = pdfUrl || (pdfId ? `http://localhost:8090/api/pdf-files/${pdfId}/download` : null);

  // ===== OBJECT FLATTENING =====

  const flattenObjects = (objects: PdfObjectsByType | undefined): FlatPdfObject[] => {
    if (!objects) return [];

    const flattened: FlatPdfObject[] = [];

    // Text words -> word
    objects.text_words?.forEach(obj => {
      flattened.push({
        type: 'word',
        page: obj.page - 1, // Convert to 0-based for frontend
        bbox: obj.bbox,
        text: obj.text,
        fontname: obj.fontname,
        fontsize: obj.fontsize
      });
    });

    // Text lines -> text_line
    objects.text_lines?.forEach(obj => {
      flattened.push({
        type: 'text_line',
        page: obj.page - 1, // Convert to 0-based
        bbox: obj.bbox
      });
    });

    // Graphic rects -> rect
    objects.graphic_rects?.forEach(obj => {
      flattened.push({
        type: 'rect',
        page: obj.page - 1, // Convert to 0-based
        bbox: obj.bbox,
        linewidth: obj.linewidth
      });
    });

    // Graphic lines -> graphic_line
    objects.graphic_lines?.forEach(obj => {
      flattened.push({
        type: 'graphic_line',
        page: obj.page - 1, // Convert to 0-based
        bbox: obj.bbox,
        linewidth: obj.linewidth
      });
    });

    // Graphic curves -> curve
    objects.graphic_curves?.forEach(obj => {
      flattened.push({
        type: 'curve',
        page: obj.page - 1, // Convert to 0-based
        bbox: obj.bbox,
        points: obj.points,
        linewidth: obj.linewidth
      });
    });

    // Images -> image
    objects.images?.forEach(obj => {
      flattened.push({
        type: 'image',
        page: obj.page - 1, // Convert to 0-based
        bbox: obj.bbox,
        format: obj.format,
        colorspace: obj.colorspace,
        bits: obj.bits
      });
    });

    // Tables -> table
    objects.tables?.forEach(obj => {
      flattened.push({
        type: 'table',
        page: obj.page - 1, // Convert to 0-based
        bbox: obj.bbox,
        rows: obj.rows,
        cols: obj.cols
      });
    });

    return flattened;
  };

  const flatObjects = flattenObjects(pdfObjects);

  // ===== PAGE CALCULATION =====

  const calculateScale = () => {
    if (!containerRef.current) return 1.0;
    const containerWidth = containerRef.current.clientWidth - 40; // Account for padding
    const targetScale = containerWidth / pageWidth;
    return Math.max(0.5, Math.min(2.0, targetScale));
  };

  useEffect(() => {
    const handleResize = () => {
      setScale(calculateScale());
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [pageWidth]);

  // ===== PDF DOCUMENT HANDLERS =====

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
    setTimeout(() => {
      setScale(calculateScale());
    }, 100);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setError(`Failed to load PDF: ${error.message}`);
    setLoading(false);
  };

  const onPageLoadError = (error: Error) => {
    console.error('PDF page load error:', error);
    setError(`Failed to load page: ${error.message}`);
  };

  // ===== OBJECT FILTERING =====

  // Filter objects for current page
  const currentPageObjects = flatObjects.filter((obj) => {
    return obj.page === currentPage - 1; // currentPage is 1-based, obj.page is 0-based after flattening
  });

  // Filter extraction fields for current page
  const currentPageExtractionFields = extractionFields.filter((field) => {
    return field.page === currentPage - 1; // 0-based page indexing
  });

  // Debug: Log when objects change
  if (flatObjects.length > 0) {
    console.log(`PdfViewer: ${flatObjects.length} total objects, ${currentPageObjects.length} on page ${currentPage}`);
  }

  // ===== RENDERING FUNCTIONS =====

  const renderObjectOverlay = (obj: FlatPdfObject, index: number) => {
    const [x0, y0, x1, y1] = obj.bbox;

    // Convert PDF coordinates to screen coordinates
    // ONLY flip Y coordinates for objects that are NOT table or curve
    const actualPdfHeight = pageHeight;
    let screenY0, screenY1;

    if (obj.type === 'table' || obj.type === 'curve') {
      // Don't flip Y coordinates for table and curve objects
      screenY0 = y0;
      screenY1 = y1;
    } else {
      // Flip Y coordinates for all other object types
      screenY0 = actualPdfHeight - y1;
      screenY1 = actualPdfHeight - y0;
    }

    // Generate object ID for selection tracking
    const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
    const isSelected = selectedObjects?.has(objectId) || false;

    // Check if this object type is currently visible
    const isTypeVisible = !selectedObjectTypes || selectedObjectTypes.has(obj.type);

    // Debug text objects to check coordinate system
    if ((obj.type === 'word' || obj.type === 'text_line') && index < 5) {
      console.log(`Object ${index} (${obj.type}):`, {
        bbox: obj.bbox,
        page: obj.page,
        text: obj.text?.substring(0, 20),
        objectId,
        isSelected,
        pdfDimensions: { width: pageWidth, height: pageHeight },
        screenCoords: { screenY0, screenY1 },
        scale: scale,
        coordinates: {
          original_y0: y0,
          original_y1: y1,
          flipped_screenY0: screenY0,
          flipped_screenY1: screenY1
        }
      });
    }

    // Determine styling based on state
    let backgroundColor, border, boxShadow, transform, zIndex;

    if (isSelected && !isTypeVisible) {
      // Selected objects whose type is not shown (gray with distinct styling)
      backgroundColor = 'rgba(156, 163, 175, 0.6)';
      border = '3px solid #9ca3af';
      boxShadow = '0 0 8px rgba(156, 163, 175, 0.8), inset 0 0 0 1px rgba(255, 255, 255, 0.3)';
      transform = 'scale(1.02)';
      zIndex = 26; // Higher than normal selected objects
    } else if (isSelected) {
      // Selected objects (green)
      backgroundColor = 'rgba(34, 197, 94, 0.5)';
      border = '3px solid #22c55e';
      boxShadow = '0 0 8px rgba(34, 197, 94, 0.6), inset 0 0 0 1px rgba(34, 197, 94, 0.8)';
      transform = 'scale(1.02)';
      zIndex = 25;
    } else {
      // Default objects
      backgroundColor = OBJECT_COLORS[obj.type];
      border = `1px solid ${OBJECT_BORDER_COLORS[obj.type]}`;
      boxShadow = 'none';
      transform = 'scale(1)';
      zIndex = 10;
    }

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * scale}px`,
      top: `${screenY0 * scale}px`,
      width: `${(x1 - x0) * scale}px`,
      height: `${(screenY1 - screenY0) * scale}px`,
      backgroundColor,
      border,
      cursor: (onObjectClick || onObjectDoubleClick) ? (isSelected && !isTypeVisible ? 'not-allowed' : 'pointer') : 'default',
      zIndex,
      pointerEvents: (onObjectClick || onObjectDoubleClick) ? (isSelected && !isTypeVisible ? 'none' : 'auto') : 'none',
      boxShadow,
      transform,
      transition: 'all 0.15s ease-in-out'
    };

    return (
      <div
        key={`${obj.type}-${index}`}
        style={style}
        onClick={() => onObjectClick?.(obj)}
        onDoubleClick={() => onObjectDoubleClick?.(obj)}
        title={isSelected && !isTypeVisible
          ? `${obj.text || obj.type} - Selected (type hidden, cannot deselect)`
          : obj.text || `${obj.type} object`
        }
        className={`transition-all ${isSelected ? 'animate-pulse' : 'hover:opacity-80 hover:scale-105'}`}
      />
    );
  };

  const renderExtractionFieldOverlay = (field: ExtractionField) => {
    const [x0, y0, x1, y1] = field.boundingBox;

    // Convert PDF coordinates to screen coordinates (flip Y)
    const actualPdfHeight = pageHeight;
    const screenY0 = actualPdfHeight - y1; // Flip Y coordinate
    const screenY1 = actualPdfHeight - y0;

    const isSelected = selectedExtractionField === field.id;

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * scale}px`,
      top: `${screenY0 * scale}px`,
      width: `${(x1 - x0) * scale}px`,
      height: `${(screenY1 - screenY0) * scale}px`,
      backgroundColor: isSelected ? 'rgba(168, 85, 247, 0.4)' : 'rgba(168, 85, 247, 0.25)',
      border: isSelected ? '4px solid #a855f7' : '3px solid #a855f7',
      borderRadius: '6px',
      cursor: isReadOnly ? 'default' : 'pointer',
      zIndex: isSelected ? 35 : 30,
      pointerEvents: 'auto',
      boxShadow: '0 0 12px rgba(168, 85, 247, 0.6), inset 0 0 0 1px rgba(255, 255, 255, 0.1)',
      transition: 'all 0.15s ease-in-out'
    };

    return (
      <div
        key={`extraction-field-${field.id}`}
        style={style}
        onClick={() => {
          if (!isReadOnly) {
            // Create a fake object for the click handler
            const fakeObj: FlatPdfObject = {
              type: 'word', // Use word type as default
              page: field.page,
              bbox: field.boundingBox,
              text: field.label
            };
            onObjectClick?.(fakeObj);
          }
        }}
        title={`Extraction Field: ${field.label}`}
        className="hover:scale-105 group"
      >
        {/* Field Label - only show on hover */}
        <div
          className="opacity-0 group-hover:opacity-100 transition-opacity duration-200"
          style={{
            position: 'absolute',
            top: '-25px',
            left: '0px',
            backgroundColor: '#a855f7',
            color: 'white',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 'bold',
            whiteSpace: 'nowrap',
            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
            zIndex: 1
          }}
        >
          {field.label}
        </div>
      </div>
    );
  };

  const renderTempFieldOverlay = (field: {id: string, boundingBox: [number, number, number, number], page: number}) => {
    const [x0, y0, x1, y1] = field.boundingBox;

    // Convert PDF coordinates to screen coordinates (flip Y)
    const actualPdfHeight = pageHeight;
    const screenY0 = actualPdfHeight - y1; // Flip Y coordinate
    const screenY1 = actualPdfHeight - y0;

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * scale}px`,
      top: `${screenY0 * scale}px`,
      width: `${(x1 - x0) * scale}px`,
      height: `${(screenY1 - screenY0) * scale}px`,
      backgroundColor: 'rgba(34, 197, 94, 0.25)',  // Green background for temporary field
      border: '3px dashed #22c55e',  // Dashed border to indicate it's temporary
      borderRadius: '6px',
      cursor: 'pointer',
      zIndex: 35,  // Higher than saved fields
      pointerEvents: 'auto',
      boxShadow: '0 0 12px rgba(34, 197, 94, 0.6), inset 0 0 0 1px rgba(255, 255, 255, 0.1)',
      animation: 'pulse 2s infinite',  // Subtle animation to draw attention
      transition: 'all 0.15s ease-in-out'
    };

    return (
      <div
        key={`temp-field-${field.id}`}
        style={style}
        title="Temporary Field (not saved yet)"
        className="group"
      >
        {/* Label overlay for temporary field - only show on hover */}
        <div
          className="opacity-0 group-hover:opacity-100 transition-opacity duration-200"
          style={{
            position: 'absolute',
            top: '-25px',
            left: '0px',
            backgroundColor: '#22c55e',
            color: 'white',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 'bold',
            whiteSpace: 'nowrap',
            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
            zIndex: 1
          }}
        >
          New Field
        </div>
      </div>
    );
  };

  const renderDrawingBox = () => {
    if (!drawingBox) return null;

    // Normalize coordinates (handle negative width/height)
    const x = drawingBox.width >= 0 ? drawingBox.x : drawingBox.x + drawingBox.width;
    const y = drawingBox.height >= 0 ? drawingBox.y : drawingBox.y + drawingBox.height;
    const width = Math.abs(drawingBox.width);
    const height = Math.abs(drawingBox.height);

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x * scale}px`,
      top: `${y * scale}px`,
      width: `${width * scale}px`,
      height: `${height * scale}px`,
      backgroundColor: 'rgba(59, 130, 246, 0.2)',
      border: '2px dashed #3b82f6',
      borderRadius: '4px',
      pointerEvents: 'none',
      zIndex: 40
    };

    return <div style={style} />;
  };

  // ===== RENDER COMPONENT =====

  if (!effectivePdfUrl) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-gray-500">No PDF URL provided</div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`flex flex-col h-full ${className}`}>
      {/* PDF Controls */}
      <div className="flex items-center justify-between p-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage <= 1}
            className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded"
          >
            ← Previous
          </button>
          <span className="text-sm text-gray-300">
            Page {currentPage} of {numPages || '?'}
          </span>
          <button
            onClick={() => setCurrentPage(prev => Math.min(numPages || prev, prev + 1))}
            disabled={currentPage >= (numPages || 0)}
            className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded"
          >
            Next →
          </button>
        </div>

        <div className="flex items-center space-x-4">
          <button
            onClick={() => setScale(prev => Math.max(0.5, prev - 0.1))}
            className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded"
          >
            Zoom Out
          </button>
          <span className="text-sm text-gray-300">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale(prev => Math.min(2.0, prev + 0.1))}
            className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded"
          >
            Zoom In
          </button>
        </div>
      </div>

      {/* PDF Document */}
      <div className="flex-1 overflow-auto bg-gray-900 p-4">
        <div className="flex justify-center">
          <Document
            file={effectivePdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={<div className="text-white">Loading PDF...</div>}
            error={<div className="text-red-400">Failed to load PDF</div>}
          >
            {loading && (
              <div className="flex items-center justify-center h-96">
                <div className="text-white">Loading PDF document...</div>
              </div>
            )}

            {error && (
              <div className="flex items-center justify-center h-96">
                <div className="text-center text-red-400">
                  <div className="text-xl mb-2">❌ Error</div>
                  <div>{error}</div>
                </div>
              </div>
            )}

            {!loading && !error && (
              <div
                ref={(el) => {
                  if (el) pageRefs.current[currentPage] = el;
                }}
                className={`relative ${isReadOnly ? 'cursor-default' : isDrawingMode ? 'cursor-crosshair' : 'cursor-default'}`}
                onMouseDown={(e) => {
                  if (!isReadOnly && pageRefs.current[currentPage] && onMouseDown) {
                    onMouseDown(e, pageRefs.current[currentPage], currentPage, scale, pageHeight);
                  }
                }}
                onMouseMove={(e) => {
                  if (!isReadOnly && pageRefs.current[currentPage] && onMouseMove) {
                    onMouseMove(e, pageRefs.current[currentPage], currentPage, scale, pageHeight);
                  }
                }}
                onMouseUp={(e) => {
                  if (!isReadOnly && pageRefs.current[currentPage] && onMouseUp) {
                    onMouseUp(e, pageRefs.current[currentPage], currentPage, scale, pageHeight);
                  }
                }}
              >
                <Page
                  pageNumber={currentPage}
                  scale={scale}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  loading=""
                  error=""
                  onLoadSuccess={(page) => {
                    try {
                      // Get the actual PDF page dimensions
                      const viewport = page.getViewport({ scale: 1.0 });
                      setPageWidth(viewport.width);
                      setPageHeight(viewport.height);
                      console.log('PDF Page dimensions:', {
                        width: viewport.width,
                        height: viewport.height,
                        scale: scale
                      });
                    } catch (error) {
                      console.error('Error getting page dimensions:', error);
                      // Use fallback dimensions if viewport fails
                      setPageWidth(612);
                      setPageHeight(792);
                    }
                  }}
                  onLoadError={onPageLoadError}
                />

                {/* Object Overlays */}
                {showObjectOverlays && (
                  <>
                    {currentPageObjects.map((obj, index) => renderObjectOverlay(obj, index))}
                  </>
                )}

                {/* Extraction Field Overlays */}
                {currentPageExtractionFields.map((field) => renderExtractionFieldOverlay(field))}

                {/* Temporary Field Overlay */}
                {tempFieldData && tempFieldData.page === currentPage - 1 && (
                  renderTempFieldOverlay(tempFieldData)
                )}

                {/* Drawing Box */}
                {renderDrawingBox()}
              </div>
            )}
          </Document>
        </div>
      </div>
    </div>
  );
}