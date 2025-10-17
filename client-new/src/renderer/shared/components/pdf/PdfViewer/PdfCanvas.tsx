/**
 * PdfCanvas
 * Wraps react-pdf Document and Page components, handles rendering and reports dimensions
 */

import { ReactNode, useState, useEffect } from 'react';
import { Document, Page } from 'react-pdf';
import { usePdfViewer } from './PdfViewerContext';

export interface PdfCanvasProps {
  pdfUrl: string;
  onError?: (error: Error) => void;
  children?: ReactNode;
}

export function PdfCanvas({ pdfUrl, onError, children }: PdfCanvasProps) {
  const {
    scale,
    currentPage,
    pdfDimensions,
    onDocumentLoadSuccess,
    onPageRenderSuccess,
  } = usePdfViewer();

  const [isDocumentLoaded, setIsDocumentLoaded] = useState(false);

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

  const handlePageLoadSuccess = (page: any) => {
    // CRITICAL: Always get PDF dimensions at scale 1.0
    // The page object's width/height properties return SCALED dimensions at the current zoom.
    // We need CONSTANT base dimensions so overlays can calculate their size as: baseDimension * scale
    // Without this, we'd get double-scaling: (alreadyScaledDimension) * scale = wrong size
    const viewport = page.originalWidth && page.originalHeight
      ? { width: page.originalWidth, height: page.originalHeight }
      : page.getViewport({ scale: 1.0 });
    onPageRenderSuccess({ width: viewport.width, height: viewport.height });
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
    <div className="flex-1 overflow-auto bg-gray-800">
      <div className="p-4" style={{ minHeight: '100%', minWidth: '100%' }}>
        <div
          className="relative"
          style={{
            width: 'fit-content',
            margin: '0 auto' // Centers when content is smaller than container
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
              <div className="relative">
                <Page
                  pageNumber={currentPage}
                  scale={scale}
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
                    style={{
                      pointerEvents: 'none',
                    }}
                  >
                    {children}
                  </div>
                )}
              </div>
            )}
          </Document>
        </div>
      </div>
    </div>
  );
}
