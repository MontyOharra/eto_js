import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Configure PDF.js worker - use local worker from node_modules
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

interface PdfObject {
  type: 'word' | 'text_line' | 'rect' | 'graphic_line' | 'curve' | 'image' | 'table' | 'extraction-field';
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  width: number;
  height: number;
  text?: string;
  metadata?: {
    fontname?: string;
    fontsize?: number;
    linewidth?: number;
    points?: number[][];
    format?: string;
    colorspace?: string;
    bits?: number;
    rows?: number;
    cols?: number;
  };
  [key: string]: any;
}

interface ExtractionField {
  id: string;
  boundingBox: [number, number, number, number];
  page: number;
  label: string;
}

interface PdfViewerProps {
  pdfUrl?: string;
  pdfId?: number; // Alternative to pdfUrl - will construct URL from ID
  objects?: PdfObject[];
  className?: string;
  showObjectOverlays?: boolean;
  onObjectClick?: (object: PdfObject) => void;
  onObjectDoubleClick?: (object: PdfObject) => void;
  selectedObjectTypes?: Set<string>;
  selectedObjects?: Set<string>;
  extractionFields?: ExtractionField[];
  selectedExtractionField?: string | null; // Highlight a specific extraction field
  isReadOnly?: boolean; // Disable interactions when true
  // Box drawing props
  isDrawingMode?: boolean;
  drawingBox?: {x: number, y: number, width: number, height: number} | null;
  tempFieldData?: {id: string, boundingBox: [number, number, number, number], page: number} | null;
  onMouseDown?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onMouseMove?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onMouseUp?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
}

const OBJECT_COLORS = {
  word: 'rgba(255, 0, 0, 0.2)',
  text_line: 'rgba(0, 255, 0, 0.2)',
  rect: 'rgba(0, 0, 255, 0.2)',
  graphic_line: 'rgba(255, 255, 0, 0.2)',
  curve: 'rgba(255, 0, 255, 0.2)',
  image: 'rgba(0, 255, 255, 0.2)',
  table: 'rgba(255, 165, 0, 0.3)'
};

const OBJECT_BORDER_COLORS = {
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
  objects = [],
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
  const [pageWidth, setPageWidth] = useState<number>(612); // Default Letter width (many PDFs use this)
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<{ [key: number]: HTMLDivElement }>({});

  // Determine the PDF URL to use
  const effectivePdfUrl = pdfUrl || (pdfId ? `http://localhost:8090/api/pdf-files/${pdfId}/download` : null);

  // Calculate scale to fit container
  const calculateScale = () => {
    if (containerRef.current) {
      const containerWidth = containerRef.current.clientWidth;
      const pdfWidth = 595; // Standard PDF width in points (A4)
      return Math.min(containerWidth / pdfWidth, 1.5); // Max scale 1.5x
    }
    return 1.0;
  };

  useEffect(() => {
    const handleResize = () => {
      setScale(calculateScale());
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
    setTimeout(() => {
      setScale(calculateScale());
      // Try to get actual page dimensions (this is a rough approach)
      // Most PDFs will be either A4 (842) or Letter (792)
      // We might need to get this from the actual page rendering
    }, 100);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setError(`Failed to load PDF: ${error.message}`);
    setLoading(false);
  };

  const onPageLoadError = (error: Error) => {
    console.error('PDF page load error:', error);
    // Don't set the main error state for page load errors, just log them
    // The page component will handle its own error display
  };

  const goToPreviousPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  };

  const goToNextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, numPages || 1));
  };

  const zoomIn = () => {
    setScale((prev) => Math.min(prev * 1.2, 3.0));
  };

  const zoomOut = () => {
    setScale((prev) => Math.max(prev / 1.2, 0.5));
  };

  const resetZoom = () => {
    setScale(calculateScale());
  };

  // Filter objects for current page and selected types
  // Also include objects that are selected even if their type is not shown
  const currentPageObjects = objects.filter((obj) => {
    const isCurrentPage = obj.page === currentPage - 1; // Objects use 0-based page indexing
    const isSelectedType = !selectedObjectTypes || selectedObjectTypes.has(obj.type);
    
    // Generate object ID to check if this object is selected
    const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
    const isObjectSelected = selectedObjects?.has(objectId) || false;
    
    // Show object if it's on current page AND (its type is selected OR the object itself is selected)
    return isCurrentPage && (isSelectedType || isObjectSelected);
  });

  // Filter extraction fields for current page
  const currentPageExtractionFields = extractionFields.filter((field) => {
    return field.page === currentPage - 1; // 0-based page indexing
  });

  // Debug: Log when objects change
  if (objects.length > 0) {
    console.log(`PdfViewer: ${objects.length} total objects, ${currentPageObjects.length} on page ${currentPage}`);
  }

  const renderObjectOverlay = (obj: PdfObject, index: number) => {
    const [x0, y0, x1, y1] = obj.bbox;

    // Convert PDF coordinates to screen coordinates
    // Flip Y coordinates for all objects EXCEPT table and curve objects
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
    
    // Objects should not be highlighted based on extraction fields
    // The extraction field boxes themselves are the visual indicators
    const hasExtractionField = false;
    
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
    
    // Check if this object type is currently visible
    const isTypeVisible = !selectedObjectTypes || selectedObjectTypes.has(obj.type);
    
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
    } else if (hasExtractionField) {
      // Objects with extraction fields defined (purple)
      backgroundColor = 'rgba(168, 85, 247, 0.5)';
      border = '2px solid #a855f7';
      boxShadow = '0 0 6px rgba(168, 85, 247, 0.6)';
      transform = 'scale(1.01)';
      zIndex = 20;
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
          : hasExtractionField 
            ? `${obj.text || obj.type} - Has extraction field` 
            : obj.text || `${obj.type} object`
        }
        className={`transition-all ${isSelected ? 'animate-pulse' : hasExtractionField ? 'animate-pulse' : 'hover:opacity-80 hover:scale-105'}`}
      />
    );
  };

  const renderExtractionFieldOverlay = (field: ExtractionField) => {
    const [x0, y0, x1, y1] = field.boundingBox;
    
    // Convert PDF coordinates to screen coordinates
    const actualPdfHeight = pageHeight;
    const screenY0 = actualPdfHeight - y1; // Flip Y coordinate
    const screenY1 = actualPdfHeight - y0;
    
    // Check if this field is selected
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
            const fakeObj: PdfObject = {
              type: 'extraction-field',
              page: field.page,
              bbox: field.boundingBox,
              text: field.label,
              width: field.boundingBox[2] - field.boundingBox[0],
              height: field.boundingBox[3] - field.boundingBox[1]
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
    
    // Convert PDF coordinates to screen coordinates
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
            top: '-32px',
            left: '0px',
            backgroundColor: '#22c55e',
            color: 'white',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: 500,
            whiteSpace: 'nowrap',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
            zIndex: 40
          }}
        >
          New Field (unsaved)
        </div>
      </div>
    );
  };

  const renderDrawingBox = () => {
    if (!drawingBox) return null;
    
    // Handle negative width/height by normalizing the box position and size
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
      zIndex: 40,
      pointerEvents: 'none'
    };

    return (
      <div
        key="drawing-box"
        style={style}
        className="animate-pulse"
      />
    );
  };

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-800 text-red-400 p-8 ${className}`}>
        <div className="text-center">
          <div className="text-xl mb-2">❌ PDF Load Error</div>
          <div className="text-sm">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col bg-gray-900 text-white ${className}`}>
      {/* PDF Viewer Controls */}
      <div className="flex items-center justify-between p-4 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <button
              onClick={goToPreviousPage}
              disabled={currentPage <= 1}
              className="px-3 py-1 text-sm bg-gray-600 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded"
            >
              ← Previous
            </button>
            <span className="text-sm">
              Page {currentPage} of {numPages || 0}
            </span>
            <button
              onClick={goToNextPage}
              disabled={currentPage >= (numPages || 1)}
              className="px-3 py-1 text-sm bg-gray-600 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded"
            >
              Next →
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={zoomOut}
            className="px-2 py-1 text-sm bg-gray-600 hover:bg-gray-700 rounded"
          >
            −
          </button>
          <span className="text-sm w-16 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="px-2 py-1 text-sm bg-gray-600 hover:bg-gray-700 rounded"
          >
            +
          </button>
          <button
            onClick={resetZoom}
            className="px-2 py-1 text-sm bg-gray-600 hover:bg-gray-700 rounded"
          >
            Fit
          </button>
        </div>
      </div>

      {/* PDF Document Container */}
      <div
        ref={containerRef}
        className="flex-1 bg-gray-700 p-4 pdf-scroll-container"
        style={{ 
          minHeight: '400px', 
          maxHeight: 'calc(100vh - 120px)',
          width: '100%',
          overflow: 'auto'
        }}
      >
        <div className="flex justify-center" style={{ minWidth: 'fit-content', minHeight: '100%' }}>
          <div className="relative bg-white shadow-lg" style={{ display: 'inline-block' }}>
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                <div className="text-gray-600">Loading PDF...</div>
              </div>
            )}
            
            <Document
              file={effectivePdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading=""
              error=""
            >
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
                  <div className="absolute inset-0 pointer-events-none">
                    {currentPageObjects.map((obj, index) => renderObjectOverlay(obj, index))}
                  </div>
                )}
                
                {/* Extraction Field Overlays */}
                <div className="absolute inset-0 pointer-events-none">
                  {currentPageExtractionFields.map((field) => renderExtractionFieldOverlay(field))}
                </div>
                
                {/* Temporary Field Overlay (unsaved field being edited) */}
                {tempFieldData && tempFieldData.page === currentPage - 1 && (
                  <div className="absolute inset-0 pointer-events-none">
                    {renderTempFieldOverlay(tempFieldData)}
                  </div>
                )}
                
                {/* Drawing Box Overlay */}
                {isDrawingMode && (
                  <div className="absolute inset-0 pointer-events-none">
                    {renderDrawingBox()}
                  </div>
                )}
              </div>
            </Document>
          </div>
        </div>
      </div>

      {/* Object Stats */}
      {showObjectOverlays && objects.length > 0 && (
        <div className="p-2 bg-gray-800 border-t border-gray-700 text-xs text-gray-400">
          Page {currentPage}: {currentPageObjects.length} objects visible
          {selectedObjectTypes && selectedObjectTypes.size > 0 && (
            <span> | Showing: {Array.from(selectedObjectTypes).join(', ')}</span>
          )}
        </div>
      )}
    </div>
  );
}