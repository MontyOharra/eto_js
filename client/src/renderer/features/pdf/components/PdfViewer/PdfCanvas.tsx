/**
 * PdfCanvas
 * Wraps react-pdf Document and Page components, handles rendering and reports dimensions
 */

import { ReactNode, useState, useEffect, useRef } from 'react';
import { Document, Page } from 'react-pdf';
import { usePdfViewer } from './PdfViewerContext';

export interface PdfCanvasProps {
  pdfUrl: string;
  onError?: (error: Error) => void;
  children?: ReactNode;
  // Optional mouse event handlers for drawing mode
  onMouseDown?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onMouseMove?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onMouseUp?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
  onClick?: (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => void;
}

export function PdfCanvas({ pdfUrl, onError, children, onMouseDown, onMouseMove, onMouseUp, onClick }: PdfCanvasProps) {
  const {
    scale, // User's zoom level
    currentPage, // Current PDF page to render
    pdfDimensions,
    setScale,
    onDocumentLoadSuccess,
    onPageRenderSuccess,
  } = usePdfViewer();

  const [isDocumentLoaded, setIsDocumentLoaded] = useState(false);
  const pageWrapperRef = useRef<HTMLDivElement>(null);

  // Fixed high-quality render scale
  // By rendering at max quality (3.0) and CSS scaling down, we avoid blur entirely
  // CSS scaling down (or 1:1) is always sharp; only scaling up causes blur
  const RENDER_SCALE = 3.0;

  // Reset document loaded state when PDF URL changes
  useEffect(() => {
    setIsDocumentLoaded(false);
  }, [pdfUrl]);

  const handleDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setIsDocumentLoaded(true);
    onDocumentLoadSuccess(numPages);
  };

  const handleDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setIsDocumentLoaded(false);
    onError?.(error);
  };

  const handlePageLoadSuccess = (page: { originalWidth?: number; originalHeight?: number; getViewport: (options: { scale: number }) => { width: number; height: number } }) => {
    // CRITICAL: Always get PDF dimensions at scale 1.0
    // The page object's width/height properties return SCALED dimensions at the current zoom.
    // We need CONSTANT base dimensions so overlays can calculate their size as: baseDimension * scale
    // Without this, we'd get double-scaling: (alreadyScaledDimension) * scale = wrong size
    const viewport = page.originalWidth && page.originalHeight
      ? { width: page.originalWidth, height: page.originalHeight }
      : page.getViewport({ scale: 1.0 });
    onPageRenderSuccess({ width: viewport.width, height: viewport.height });
  };

  const handleWheel = (e: React.WheelEvent) => {
    // Only handle Ctrl+Scroll for zoom
    if (e.ctrlKey) {
      e.preventDefault();

      // Calculate zoom delta (negative deltaY = zoom in, positive = zoom out)
      const zoomDelta = -e.deltaY * 0.001; // Adjust sensitivity
      const newScale = Math.max(0.5, Math.min(3.0, scale + zoomDelta));

      setScale(newScale);
    }
  };

  // Don't render if no PDF URL
  if (!pdfUrl) {
    return (
      <div className="flex-1 overflow-auto bg-gray-800">
        <div className="flex items-center justify-center h-96">
          <p className="text-gray-400">No PDF selected</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-auto bg-gray-800 relative px-4" onWheel={handleWheel}>
      <div className="pb-4" style={{ minHeight: '100%', minWidth: '100%' }}>
        <div
          className="relative"
          style={{
            width: 'fit-content',
            margin: '0 auto', // Centers when small, allows full scroll when large
          }}
        >
          <Document
            key={pdfUrl} // Force remount when URL changes
            file={pdfUrl}
            onLoadSuccess={handleDocumentLoadSuccess}
            onLoadError={handleDocumentLoadError}
            loading={
              <div className="flex items-center justify-center h-96">
                <p className="text-gray-400">Loading PDF...</p>
              </div>
            }
            error={
              <div className="flex items-center justify-center h-96">
                <p className="text-red-400">Failed to load PDF</p>
              </div>
            }
          >
            {isDocumentLoaded && (
              // Wrapper with explicit dimensions for proper scrollbar behavior
              // CSS transforms don't affect layout, so we need this wrapper to tell
              // the browser the actual visual size for scrolling
              <div
                style={{
                  width: pdfDimensions ? `${pdfDimensions.width * scale}px` : 'auto',
                  height: pdfDimensions ? `${pdfDimensions.height * scale}px` : 'auto',
                  position: 'relative',
                  overflow: 'hidden', // Clip the scaled content to wrapper bounds
                }}
              >
                <div
                  ref={pageWrapperRef}
                  className="relative"
                  style={{
                    transform: `scale(${scale / RENDER_SCALE})`,
                    transformOrigin: 'top left',
                    width: pdfDimensions ? `${pdfDimensions.width * RENDER_SCALE}px` : 'auto',
                    height: pdfDimensions ? `${pdfDimensions.height * RENDER_SCALE}px` : 'auto',
                  }}
                >
                  <Page
                    pageNumber={currentPage}
                    scale={RENDER_SCALE}
                    renderTextLayer={false}
                    renderAnnotationLayer={false}
                    loading=""
                    error=""
                    onLoadSuccess={handlePageLoadSuccess}
                  />
                  {/* Overlay container - positioned absolutely over the PDF */}
                  {pdfDimensions && children && (
                    <div
                      className="absolute top-0 left-0 w-full h-full"
                      onMouseDown={(e) => {
                        if (onMouseDown && pageWrapperRef.current) {
                          onMouseDown(e, pageWrapperRef.current, currentPage, scale, pdfDimensions.height);
                        }
                      }}
                      onMouseMove={(e) => {
                        if (onMouseMove && pageWrapperRef.current) {
                          onMouseMove(e, pageWrapperRef.current, currentPage, scale, pdfDimensions.height);
                        }
                      }}
                      onMouseUp={(e) => {
                        if (onMouseUp && pageWrapperRef.current) {
                          onMouseUp(e, pageWrapperRef.current, currentPage, scale, pdfDimensions.height);
                        }
                      }}
                      onClick={(e) => {
                        if (onClick && pageWrapperRef.current) {
                          onClick(e, pageWrapperRef.current, currentPage, scale, pdfDimensions.height);
                        }
                      }}
                    >
                      {children}
                    </div>
                  )}
                </div>
              </div>
            )}
          </Document>
        </div>
      </div>
    </div>
  );
}
