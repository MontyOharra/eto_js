import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface PdfObject {
  type: 'word' | 'text_line' | 'rect' | 'graphic_line' | 'curve' | 'image' | 'table';
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  width: number;
  height: number;
  text?: string;
  [key: string]: any;
}

interface PdfViewerProps {
  pdfUrl: string;
  objects?: PdfObject[];
  className?: string;
  showObjectOverlays?: boolean;
  onObjectClick?: (object: PdfObject) => void;
  selectedObjectTypes?: Set<string>;
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
  objects = [],
  className = '',
  showObjectOverlays = true,
  onObjectClick,
  selectedObjectTypes
}: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<{ [key: number]: HTMLDivElement }>({});

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
    }, 100);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setError(`Failed to load PDF: ${error.message}`);
    setLoading(false);
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
  const currentPageObjects = objects.filter((obj) => {
    const isCurrentPage = obj.page === currentPage - 1; // Objects use 0-based page indexing
    const isSelectedType = !selectedObjectTypes || selectedObjectTypes.has(obj.type);
    return isCurrentPage && isSelectedType;
  });

  const renderObjectOverlay = (obj: PdfObject, index: number) => {
    const [x0, y0, x1, y1] = obj.bbox;
    
    // Convert PDF coordinates to screen coordinates
    // PDF coordinates: origin at bottom-left, Y increases upward
    // Screen coordinates: origin at top-left, Y increases downward
    const pdfHeight = 842; // Standard A4 height in points
    const screenY0 = pdfHeight - y1; // Flip Y coordinate
    const screenY1 = pdfHeight - y0;
    
    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * scale}px`,
      top: `${screenY0 * scale}px`,
      width: `${(x1 - x0) * scale}px`,
      height: `${(screenY1 - screenY0) * scale}px`,
      backgroundColor: OBJECT_COLORS[obj.type],
      border: `1px solid ${OBJECT_BORDER_COLORS[obj.type]}`,
      cursor: onObjectClick ? 'pointer' : 'default',
      zIndex: 10,
      pointerEvents: onObjectClick ? 'auto' : 'none'
    };

    return (
      <div
        key={`${obj.type}-${index}`}
        style={style}
        onClick={() => onObjectClick?.(obj)}
        title={obj.text || `${obj.type} object`}
        className="hover:opacity-80 transition-opacity"
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
        className="flex-1 overflow-auto bg-gray-700 p-4"
        style={{ minHeight: '400px' }}
      >
        <div className="flex justify-center">
          <div className="relative bg-white shadow-lg">
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                <div className="text-gray-600">Loading PDF...</div>
              </div>
            )}
            
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading=""
              error=""
            >
              <div
                ref={(el) => {
                  if (el) pageRefs.current[currentPage] = el;
                }}
                className="relative"
              >
                <Page
                  pageNumber={currentPage}
                  scale={scale}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  loading=""
                  error=""
                />
                
                {/* Object Overlays */}
                {showObjectOverlays && (
                  <div className="absolute inset-0 pointer-events-none">
                    {currentPageObjects.map((obj, index) => renderObjectOverlay(obj, index))}
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