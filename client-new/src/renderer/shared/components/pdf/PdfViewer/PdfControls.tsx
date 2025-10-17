/**
 * PdfControls
 * Provides zoom and pagination controls with flexible positioning
 */

import { usePdfViewer } from './PdfViewerContext';

export interface PdfControlsProps {
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  showZoom?: boolean;
  showPagination?: boolean;
  className?: string;
}

export function PdfControls({
  position = 'bottom-center',
  showZoom = true,
  showPagination = true,
  className = '',
}: PdfControlsProps) {
  const {
    scale,
    currentPage,
    numPages,
    goToNextPage,
    goToPreviousPage,
    zoomIn,
    zoomOut,
  } = usePdfViewer();

  // Position classes mapping
  const positionClasses = {
    'top-left': 'top-2 left-2',
    'top-center': 'top-2 left-1/2 transform -translate-x-1/2',
    'top-right': 'top-2 right-2',
    'bottom-left': 'bottom-2 left-2',
    'bottom-center': 'bottom-2 left-1/2 transform -translate-x-1/2',
    'bottom-right': 'bottom-2 right-2',
  };

  return (
    <div
      className={`absolute ${positionClasses[position]} bg-gray-900/90 backdrop-blur-sm border border-gray-600 rounded-lg p-2 flex items-center space-x-3 z-10 ${className}`}
    >
      {/* Page Navigation */}
      {showPagination && (
        <div className="flex items-center space-x-2">
          <button
            onClick={goToPreviousPage}
            disabled={currentPage <= 1}
            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
            title="Previous page"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-300 min-w-[80px] text-center">
            Page {currentPage} of {numPages || '?'}
          </span>
          <button
            onClick={goToNextPage}
            disabled={currentPage >= (numPages || 0)}
            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
            title="Next page"
          >
            Next →
          </button>
        </div>
      )}

      {/* Divider */}
      {showPagination && showZoom && (
        <div className="h-6 w-px bg-gray-600"></div>
      )}

      {/* Zoom Controls */}
      {showZoom && (
        <div className="flex items-center space-x-2">
          <button
            onClick={zoomOut}
            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
            title="Zoom out"
          >
            −
          </button>
          <span className="text-xs text-gray-300 min-w-[45px] text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
            title="Zoom in"
          >
            +
          </button>
        </div>
      )}
    </div>
  );
}
