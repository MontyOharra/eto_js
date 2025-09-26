import React, { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

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

interface PdfObjects {
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
  description: string;
  required: boolean;
  validationRegex?: string;
}

interface PdfViewerProps {
  pdfUrl: string;
  pdfObjects: PdfObjects;
  showObjectOverlays?: boolean;
  selectedObjectTypes?: Set<ObjectType>;
  selectedObjects?: Set<string>;
  extractionFields?: ExtractionField[];
  selectedExtractionFieldId?: string | null;
  isDrawingMode?: boolean;
  drawingBox?: {x: number, y: number, width: number, height: number} | null;
  tempFieldData?: {id: string, boundingBox: [number, number, number, number], page: number} | null;
  className?: string;
  onObjectClick?: (obj: any) => void;
  onObjectDoubleClick?: (obj: any) => void;
  onExtractionFieldClick?: (field: ExtractionField) => void;
  onMouseDown?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onMouseMove?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onMouseUp?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
}

type ObjectType = 'text_words' | 'text_lines' | 'graphic_rects' | 'graphic_lines' | 'graphic_curves' | 'images' | 'tables';

// ===== OBJECT TYPE CONFIGURATIONS =====

const OBJECT_TYPE_CONFIGS = {
  text_words: {
    label: 'Text Words',
    color: '#dc2626', // Red-600 - good contrast on white
    needsCoordinateFlip: false, // Text words use direct coordinates
    displayType: 'text_word' // For backwards compatibility
  },
  text_lines: {
    label: 'Text Lines',
    color: '#059669', // Emerald-600 - darker green, much more visible
    needsCoordinateFlip: false, // Text lines use direct coordinates
    displayType: 'text_line'
  },
  graphic_rects: {
    label: 'Rectangles',
    color: '#2563eb', // Blue-600 - good contrast
    needsCoordinateFlip: true, // Use direct coordinates like curves and tables
    displayType: 'graphic_rect'
  },
  graphic_lines: {
    label: 'Lines',
    color: '#d97706', // Amber-600 - much more visible than bright yellow
    needsCoordinateFlip: true, // Use direct coordinates like curves and tables
    displayType: 'graphic_line'
  },
  graphic_curves: {
    label: 'Curves',
    color: '#c026d3', // Fuchsia-600 - good contrast
    needsCoordinateFlip: false, // Curves display perfectly - no flip needed
    displayType: 'graphic_curve'
  },
  images: {
    label: 'Images',
    color: '#0891b2', // Cyan-600 - better than bright cyan
    needsCoordinateFlip: true, // Use direct coordinates like curves and tables
    displayType: 'image'
  },
  tables: {
    label: 'Tables',
    color: '#ea580c', // Orange-600 - good contrast
    needsCoordinateFlip: false, // Tables display perfectly - no flip needed
    displayType: 'table'
  }
} as const;

// ===== COORDINATE TRANSFORMATION UTILITIES =====

const transformCoordinates = (
  bbox: [number, number, number, number],
  pageHeight: number,
  needsFlip: boolean,
  scale: number = 1,
  objectType?: string
): [number, number, number, number] => {
  if (needsFlip) {
    // Graphics and images: flip Y coordinates and apply scale
    const result = [
      bbox[0] * scale,
      (pageHeight - bbox[3]) * scale, // Flip Y coordinate
      bbox[2] * scale,
      (pageHeight - bbox[1]) * scale  // Flip Y coordinate
    ];

    // Debug logging for coordinate transformation
    if (objectType && (objectType === 'graphic_rect' || objectType === 'graphic_line' || objectType === 'image')) {
      console.log(`Transform ${objectType}:`, {
        originalBbox: bbox,
        pageHeight,
        scale,
        transformed: result
      });
    }

    return result as [number, number, number, number];
  } else {
    // Text objects and curves: use direct coordinates with scale
    return [
      bbox[0] * scale,
      bbox[1] * scale,
      bbox[2] * scale,
      bbox[3] * scale
    ];
  }
};

export function PdfViewer_new({
  pdfUrl,
  pdfObjects,
  showObjectOverlays = false,
  selectedObjectTypes = new Set(),
  selectedObjects = new Set(),
  extractionFields = [],
  selectedExtractionFieldId = null,
  isDrawingMode = false,
  drawingBox,
  tempFieldData,
  className = '',
  onObjectClick,
  onObjectDoubleClick,
  onExtractionFieldClick,
  onMouseDown,
  onMouseMove,
  onMouseUp
}: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState(1); // 1-based index for react-pdf
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flattenedObjects, setFlattenedObjects] = useState<any[]>([]);
  const [pageHeight, setPageHeight] = useState<number>(800); // Default height
  const [hoveredObjectId, setHoveredObjectId] = useState<string | null>(null);
  const [hoveredFieldId, setHoveredFieldId] = useState<string | null>(null);

  // Determine the PDF URL to use (matching old PdfViewer pattern)
  const effectivePdfUrl = pdfUrl;

  // Debug PDF URL on mount
  useEffect(() => {
    console.log('PdfViewer_new mounted with URL:', effectivePdfUrl);
    if (!effectivePdfUrl) {
      setError('No PDF URL provided');
      setLoading(false);
    }
  }, [effectivePdfUrl]);

  // Generate unique ID for any object based on type, page, and bbox
  const generateObjectId = (type: string, page: number, bbox: [number, number, number, number]): string => {
    return `${type}-${page}-${bbox.join('-')}`;
  };

  // Flatten nested objects structure for easier processing
  useEffect(() => {
    if (!pdfObjects) {
      setFlattenedObjects([]);
      return;
    }

    const flattened: any[] = [];

    // Process each object type
    Object.entries(pdfObjects).forEach(([objectType, objects]) => {
      if (!objects || !Array.isArray(objects)) return;

      const config = OBJECT_TYPE_CONFIGS[objectType as ObjectType];
      if (!config) return;

      objects.forEach(obj => {
        const flattenedObj = {
          ...obj,
          type: config.displayType,
          objectType: objectType as ObjectType,
          color: config.color,
          needsCoordinateFlip: config.needsCoordinateFlip,
          id: generateObjectId(config.displayType, obj.page, obj.bbox)
        };
        flattened.push(flattenedObj);
      });
    });

    setFlattenedObjects(flattened);
  }, [pdfObjects]);

  // Document load handlers
  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('PDF document loaded successfully, pages:', numPages, 'URL:', effectivePdfUrl);
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF document load error:', error, 'URL:', effectivePdfUrl);
    setError('Failed to load PDF: ' + error.message);
    setLoading(false);
  };

  const onPageLoadSuccess = (page: any) => {
    // Get the actual page dimensions to align coordinates properly
    try {
      // Page object should have dimensions we can use
      console.log('Page loaded, page object:', page);

      // Try to get the height from the page - react-pdf provides dimensions
      if (page && page.originalHeight) {
        console.log('Using originalHeight:', page.originalHeight);
        setPageHeight(page.originalHeight);
      } else if (page && page.height) {
        console.log('Using height:', page.height);
        setPageHeight(page.height);
      } else {
        console.log('Using fallback height: 800');
        setPageHeight(800); // Fallback
      }
    } catch (error) {
      console.error('Error getting page dimensions:', error);
      setPageHeight(800); // Fallback
    }
  };


  // Calculate object area for size comparison
  const calculateObjectArea = (bbox: [number, number, number, number]) => {
    const width = Math.abs(bbox[2] - bbox[0]);
    const height = Math.abs(bbox[3] - bbox[1]);
    return width * height;
  };

  // Check if a point is within an object's bounding box (with grace area for thin objects)
  const isPointInObject = (x: number, y: number, obj: any, pageHeight: number, scale: number) => {
    const [x0, y0, x1, y1] = transformCoordinates(obj.bbox, pageHeight, obj.needsCoordinateFlip, scale, obj.objectType);

    let left = Math.min(x0, x1);
    let right = Math.max(x0, x1);
    let top = Math.min(y0, y1);
    let bottom = Math.max(y0, y1);

    // Add grace area for thin objects (especially lines)
    const graceArea = 3; // 3 pixels of grace area
    const width = right - left;
    const height = bottom - top;

    // Expand bounds if object is very thin
    if (width <= 2) {
      left -= graceArea;
      right += graceArea;
    }
    if (height <= 2) {
      top -= graceArea;
      bottom += graceArea;
    }

    return x >= left && x <= right && y >= top && y <= bottom;
  };

  // Find the smallest object at a given point
  const findSmallestObjectAtPoint = (x: number, y: number, pageHeight: number, scale: number) => {
    const visibleObjects = flattenedObjects.filter(obj =>
      obj.page === currentPage &&
      selectedObjectTypes.has(obj.objectType) &&
      isPointInObject(x, y, obj, pageHeight, scale)
    );

    if (visibleObjects.length === 0) return null;
    if (visibleObjects.length === 1) return visibleObjects[0];

    // Find the object with the smallest area
    return visibleObjects.reduce((smallest, current) => {
      const smallestArea = calculateObjectArea(smallest.bbox);
      const currentArea = calculateObjectArea(current.bbox);
      return currentArea < smallestArea ? current : smallest;
    });
  };

  const handleObjectClick = (obj: any, event: React.MouseEvent) => {
    event.stopPropagation();
    if (onObjectClick) {
      onObjectClick(obj);
    }
  };

  const handleObjectDoubleClick = (obj: any, event: React.MouseEvent) => {
    event.stopPropagation();
    if (onObjectDoubleClick) {
      onObjectDoubleClick(obj);
    }
  };

  // Handle smart selection on the page level
  const handleSmartClick = (event: React.MouseEvent) => {
    // Find the page container to get correct coordinates
    const pageContainer = event.currentTarget.closest('.relative.bg-white.shadow-lg') as HTMLElement;
    if (!pageContainer) return;

    const rect = pageContainer.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const smallestObject = findSmallestObjectAtPoint(x, y, pageHeight, scale);

    if (smallestObject && onObjectClick) {
      event.stopPropagation();
      onObjectClick(smallestObject);
    }
  };

  const handleSmartDoubleClick = (event: React.MouseEvent) => {
    // Find the page container to get correct coordinates
    const pageContainer = event.currentTarget.closest('.relative.bg-white.shadow-lg') as HTMLElement;
    if (!pageContainer) return;

    const rect = pageContainer.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const smallestObject = findSmallestObjectAtPoint(x, y, pageHeight, scale);

    if (smallestObject && onObjectDoubleClick) {
      event.stopPropagation();
      onObjectDoubleClick(smallestObject);
    }
  };

  // Handle smart hovering on the page level
  const handleSmartMouseEnter = (event: React.MouseEvent) => {
    // Find the page container to get correct coordinates
    const pageContainer = event.currentTarget.closest('.relative.bg-white.shadow-lg') as HTMLElement;
    if (!pageContainer) return;

    const rect = pageContainer.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const smallestObject = findSmallestObjectAtPoint(x, y, pageHeight, scale);

    if (smallestObject) {
      setHoveredObjectId(smallestObject.id);
    }
  };

  const handleSmartMouseLeave = () => {
    setHoveredObjectId(null);
  };

  const handlePageMouseDown = (e: React.MouseEvent) => {
    if (onMouseDown) {
      const pageElement = e.currentTarget as HTMLElement;
      onMouseDown(e, pageElement, currentPage, scale, pageHeight); // currentPage is already 1-based
    }
  };

  const handlePageMouseMove = (e: React.MouseEvent) => {
    if (onMouseMove) {
      const pageElement = e.currentTarget as HTMLElement;
      onMouseMove(e, pageElement, currentPage, scale, pageHeight);
    }
  };

  const handlePageMouseUp = (e: React.MouseEvent) => {
    if (onMouseUp) {
      const pageElement = e.currentTarget as HTMLElement;
      onMouseUp(e, pageElement, currentPage, scale, pageHeight);
    }
  };

  const renderObjectOverlay = (obj: any, pageIndex: number, pageHeight: number) => {
    const isVisible = selectedObjectTypes.has(obj.objectType);
    const isSelected = selectedObjects.has(obj.id);
    const isHiddenButSelected = !isVisible && isSelected;
    const isHovered = hoveredObjectId === obj.id;

    if (!isVisible && !isSelected) return null;

    const [x0, y0, x1, y1] = transformCoordinates(obj.bbox, pageHeight, obj.needsCoordinateFlip, scale, obj.objectType);

    const width = Math.abs(x1 - x0);
    const height = Math.abs(y1 - y0);
    const left = Math.min(x0, x1);
    const top = Math.min(y0, y1);

    // Determine overlay style with smart hover effects
    let overlayStyle: React.CSSProperties = {
      position: 'absolute',
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      height: `${height}px`,
      pointerEvents: isHiddenButSelected ? 'none' : 'auto', // Enable hover effects, disable clicks on hidden objects
      cursor: isHiddenButSelected ? 'default' : 'pointer',
      zIndex: isHiddenButSelected ? 5 : (isHovered ? 15 : 10), // Higher z-index when hovered
      transition: 'all 0.15s ease-in-out', // Smooth transition for hover effects
      transformOrigin: 'center', // Scale from center
      transform: isHovered && !isHiddenButSelected ? 'scale(1.05)' : 'scale(1)' // Apply hover scaling
    };

    if (isHiddenButSelected) {
      // Hidden but selected objects - gray color scheme
      overlayStyle.backgroundColor = '#6B728040'; // Gray with 25% opacity
      overlayStyle.border = `2px solid #6B7280`;
      overlayStyle.boxShadow = `0 0 0 1px #6B728080`; // Gray glow effect
      overlayStyle.opacity = '0.7'; // Additional opacity for hidden state
    } else if (isSelected) {
      // Selected and visible objects - more opaque background and larger border
      overlayStyle.backgroundColor = obj.color + '60'; // Increased from 40 to 60 (more opaque)
      overlayStyle.border = `2px solid ${obj.color}`; // Increased back to 2px for selected objects
      overlayStyle.boxShadow = `0 0 0 1px ${obj.color}80`; // Glow effect
    } else {
      // Visible but not selected - more visible styling
      overlayStyle.border = `1px solid ${obj.color}`; // Reverted back to 1px
      overlayStyle.backgroundColor = obj.color + '30'; // Kept increased opacity (more opaque)
    }

    // Add hover glow effect
    if (isHovered && !isHiddenButSelected) {
      overlayStyle.boxShadow = `0 0 8px 2px ${obj.color}60, ${overlayStyle.boxShadow || ''}`;
    }

    return (
      <div
        key={obj.id}
        style={overlayStyle}
        className={`pdf-object-overlay ${isHiddenButSelected ? 'hidden-selected' : ''}`}
        onClick={(e) => {
          if (!isHiddenButSelected) {
            // Use smart selection logic instead of direct object selection
            handleSmartClick(e);
          }
        }}
        onDoubleClick={(e) => {
          if (!isHiddenButSelected) {
            // Use smart selection logic instead of direct object selection
            handleSmartDoubleClick(e);
          }
        }}
        // No individual mouse enter/leave handlers - use smart hovering at page level
        title={
          isHiddenButSelected
            ? `${obj.type} | Page ${obj.page} | Selected but type hidden | ${obj.text || 'No text'}`
            : `${obj.type} | Page ${obj.page} | ${obj.text || 'No text'}`
        }
      />
    );
  };

  const renderExtractionFieldOverlay = (field: ExtractionField, pageIndex: number, pageHeight: number) => {
    // field.boundingBox is now stored in display coordinates (no Y-flipping needed)
    const [x0, y0, x1, y1] = transformCoordinates(field.boundingBox, pageHeight, false, scale);

    const width = Math.abs(x1 - x0);
    const height = Math.abs(y1 - y0);
    const left = Math.min(x0, x1);
    const top = Math.min(y0, y1);
    const isHovered = hoveredFieldId === field.id;
    const isSelected = selectedExtractionFieldId === field.id;

    // Selected fields use dashed border like temp fields, saved fields use solid border
    const borderStyle = isSelected ? '2px dashed #8B5CF6' : '2px solid #8B5CF6';

    return (
      <>
        {/* Main field overlay */}
        <div
          key={field.id}
          style={{
            position: 'absolute',
            left: `${left}px`,
            top: `${top}px`,
            width: `${width}px`,
            height: `${height}px`,
            backgroundColor: 'rgba(139, 92, 246, 0.15)', // Very transparent background
            border: borderStyle, // Dashed when selected, solid when saved
            borderRadius: '3px',
            pointerEvents: 'auto',
            cursor: 'pointer',
            zIndex: 15
          }}
          title={`Extraction Field: ${field.label} | ${field.description || 'No description'}`}
          onMouseEnter={() => setHoveredFieldId(field.id)}
          onMouseLeave={() => setHoveredFieldId(null)}
          onClick={() => onExtractionFieldClick?.(field)}
        />

        {/* Hover label extension - appears on top left of field box */}
        {isHovered && (
          <div
            key={`${field.id}-label`}
            style={{
              position: 'absolute',
              left: `${left}px`,
              top: `${top - 25}px`, // Position above the field box
              backgroundColor: '#8B5CF6',
              color: 'white',
              fontSize: '11px',
              fontWeight: '500',
              padding: '4px 8px',
              borderRadius: '4px',
              whiteSpace: 'nowrap',
              zIndex: 20,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
              pointerEvents: 'none' // Don't interfere with mouse events
            }}
          >
            {field.label}
          </div>
        )}
      </>
    );
  };

  const renderDrawingBox = (pageIndex: number, pageHeight: number) => {
    if (!drawingBox) return null;

    // Calculate normalized coordinates for current drawing box
    const normalizedX0 = Math.min(drawingBox.x, drawingBox.x + drawingBox.width);
    const normalizedY0 = Math.min(drawingBox.y, drawingBox.y + drawingBox.height);
    const normalizedWidth = Math.abs(drawingBox.width);
    const normalizedHeight = Math.abs(drawingBox.height);

    return (
      <div
        style={{
          position: 'absolute',
          left: `${normalizedX0 * scale}px`,
          top: `${normalizedY0 * scale}px`,
          width: `${normalizedWidth * scale}px`,
          height: `${normalizedHeight * scale}px`,
          backgroundColor: 'rgba(139, 92, 246, 0.3)',
          border: '2px dashed #8B5CF6',
          borderRadius: '3px',
          pointerEvents: 'none',
          zIndex: 20
        }}
      />
    );
  };

  const renderTempField = (pageIndex: number, pageHeight: number) => {
    if (!tempFieldData || tempFieldData.page !== (pageIndex - 1)) return null; // Convert 1-based pageIndex to 0-based

    // tempFieldData.boundingBox is now stored in display coordinates (no Y-flipping needed)
    const [x0, y0, x1, y1] = transformCoordinates(tempFieldData.boundingBox, pageHeight, false, scale);

    const width = Math.abs(x1 - x0);
    const height = Math.abs(y1 - y0);
    const left = Math.min(x0, x1);
    const top = Math.min(y0, y1);

    return (
      <div
        key={tempFieldData.id}
        style={{
          position: 'absolute',
          left: `${left}px`,
          top: `${top}px`,
          width: `${width}px`,
          height: `${height}px`,
          backgroundColor: 'transparent', // No background during creation
          border: '2px dashed #8B5CF6', // Dashed border during creation
          borderRadius: '3px',
          pointerEvents: 'none',
          zIndex: 15
        }}
      />
    );
  };

  // Early return if no PDF URL
  if (!effectivePdfUrl) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-gray-400">No PDF URL provided</div>
      </div>
    );
  }

  return (
    <div className={`pdf-viewer ${className} flex flex-col h-full`}>
      {/* Navigation and Control Bar */}
      <div className="flex-shrink-0 bg-gray-800 border-b border-gray-700 p-3">
        <div className="flex items-center justify-between">
          {/* Page Navigation */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white rounded"
              >
                ← Previous
              </button>

              <div className="flex items-center space-x-2 text-white text-sm">
                <span>Page</span>
                <input
                  type="number"
                  value={currentPage}
                  onChange={(e) => {
                    const newPage = parseInt(e.target.value);
                    if (newPage >= 1 && newPage <= numPages) {
                      setCurrentPage(newPage);
                    }
                  }}
                  min="1"
                  max={numPages}
                  className="w-16 px-2 py-1 text-center bg-gray-700 border border-gray-600 rounded text-white text-sm"
                />
                <span>of {numPages}</span>
              </div>

              <button
                onClick={() => setCurrentPage(prev => Math.min(numPages, prev + 1))}
                disabled={currentPage >= numPages}
                className="px-3 py-1 text-sm bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white rounded"
              >
                Next →
              </button>
            </div>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setScale(prev => Math.max(0.5, prev - 0.25))}
              className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded"
            >
              Zoom Out
            </button>
            <span className="px-2 py-1 text-xs text-white min-w-[60px] text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={() => setScale(prev => Math.min(3.0, prev + 0.25))}
              className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded"
            >
              Zoom In
            </button>
            <button
              onClick={() => setScale(1.0)}
              className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Current Page Container */}
      <div className="flex-1 overflow-auto bg-gray-200 p-4">
        <div className="flex justify-center">
          <Document
            file={effectivePdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={<div className="text-gray-400">Loading PDF...</div>}
            error={<div className="text-red-400">Failed to load PDF</div>}
          >
            {loading && (
              <div className="flex items-center justify-center h-96">
                <div className="text-gray-400">Loading PDF document...</div>
              </div>
            )}

            {error && (
              <div className="flex items-center justify-center h-96">
                <div className="text-red-400">Error: {error}</div>
              </div>
            )}

            {!loading && !error && numPages > 0 && (
              <div
                className="relative bg-white shadow-lg"
                style={{
                  cursor: isDrawingMode ? 'crosshair' : 'pointer'
                }}
                onMouseDown={handlePageMouseDown}
                onMouseMove={(e) => {
                  handlePageMouseMove(e);
                  handleSmartMouseEnter(e); // Update hover state as mouse moves
                }}
                onMouseLeave={handleSmartMouseLeave}
                onMouseUp={handlePageMouseUp}
                onClick={handleSmartClick}
                onDoubleClick={handleSmartDoubleClick}
              >
                {/* PDF Page using react-pdf */}
                <Page
                  pageNumber={currentPage}
                  scale={scale}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  onLoadSuccess={onPageLoadSuccess}
                  className="relative"
                />

                {/* Object Overlays for Current Page */}
                {showObjectOverlays && flattenedObjects
                  .filter(obj => obj.page === currentPage) // Now both systems use 1-based indexing
                  .map(obj => renderObjectOverlay(obj, currentPage, pageHeight))}

                {/* Extraction Field Overlays for Current Page */}
                {extractionFields
                  .filter(field => field.page === currentPage - 1) // Fields are 0-based, convert to 1-based
                  .map(field => renderExtractionFieldOverlay(field, currentPage, pageHeight))}

                {/* Drawing Box */}
                {renderDrawingBox(currentPage, pageHeight)}

                {/* Temporary Field */}
                {renderTempField(currentPage, pageHeight)}
              </div>
            )}
          </Document>
        </div>
      </div>
    </div>
  );
}