/**
 * PdfControlsSidebar
 * Vertical sidebar with page navigation and zoom slider
 */

import { useRef, useEffect } from 'react';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { usePdfViewer } from './PdfViewerContext';

export interface PdfControlsSidebarProps {
  position?: 'left' | 'right';
  className?: string;
}

const MAX_ZOOM = 300;
const MIN_ZOOM = 50;

export function PdfControlsSidebar({
  position = 'right',
  className = '',
}: PdfControlsSidebarProps) {
  const {
    scale,
    currentPage,
    numPages,
    goToNextPage,
    goToPreviousPage,
    setScale,
    pdfDimensions,
    fitToWidth,
  } = usePdfViewer();

  const sidebarRef = useRef<HTMLDivElement>(null);

  // Convert scale to percentage (0.5 = 50%, 2.0 = 200%)
  const zoomPercentage = Math.round(scale * 100);

  // Handle slider change
  const handleZoomChange = (value: number | number[]) => {
    const zoomValue = Array.isArray(value) ? value[0] : value;
    const newScale = zoomValue / 100;
    setScale(newScale);
  };

  // Fit PDF width to viewport
  const handleFitToWidth = () => {
    console.log('[PdfControlsSidebar] Fit to width button clicked');
    if (!pdfDimensions || !sidebarRef.current) {
      console.log('[PdfControlsSidebar] Missing pdfDimensions or sidebarRef');
      return;
    }

    // Get the parent container (the flex container with PDF canvas + sidebar)
    const parentContainer = sidebarRef.current.parentElement;
    if (!parentContainer) {
      console.log('[PdfControlsSidebar] No parent container');
      return;
    }

    // Use the context's fitToWidth function
    const containerWidth = parentContainer.clientWidth;
    const sidebarWidth = sidebarRef.current.clientWidth;
    console.log('[PdfControlsSidebar] Calling fitToWidth with containerWidth:', containerWidth, 'sidebarWidth:', sidebarWidth);
    fitToWidth(containerWidth, sidebarWidth);
  };

  return (
    <div
      ref={sidebarRef}
      className={`flex-shrink-0 w-16 bg-gray-900 border-gray-700 ${
        position === 'left' ? 'border-r' : 'border-l'
      } flex flex-col ${className}`}
    >
      {/* Page Navigation Section */}
      <div className="flex flex-col items-center py-4 space-y-3 border-b border-gray-700">
        {/* Previous Page Button */}
        <button
          onClick={goToPreviousPage}
          disabled={currentPage <= 1}
          className="p-2 text-white bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          title="Previous page"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M10 12L6 8L10 4"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        {/* Page Counter */}
        <div className="flex flex-col items-center">
          <span className="text-xs text-gray-300 text-center m-2">Page</span>
          <span className="text-xs text-gray-300 font-medium">{currentPage}</span>
          <span className="text-[10px] text-gray-500 p-1">of</span>
          <span className="text-xs text-gray-500 mb-2">{numPages || '?'}</span>
        </div>

        {/* Next Page Button */}
        <button
          onClick={goToNextPage}
          disabled={currentPage >= (numPages || 0)}
          className="p-2 text-white bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          title="Next page"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M6 4L10 8L6 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>

      {/* Zoom Slider Section */}
      <div className="flex-1 flex flex-col items-center py-6 px-3">
        {/* Zoom Percentage Display */}
        <div className="mb-3 text-center">
          <span className="text-xs text-gray-300 font-medium">{zoomPercentage}%</span>
        </div>

        {/* Fit to Width Button */}
        <button
          onClick={handleFitToWidth}
          disabled={!pdfDimensions}
          className="mb-3 p-2 text-white bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          title="Fit to width"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M2 8H14M2 8L5 5M2 8L5 11M14 8L11 5M14 8L11 11"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        {/* Max Zoom Indicator */}
        <div className="mb-2">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M6 2L6 10M2 6L10 6" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>

        {/* Vertical Slider - fills remaining space */}
        <div className="flex-1 w-full flex items-center justify-center px-2">
          <Slider
            vertical
            min={MIN_ZOOM}
            max={MAX_ZOOM}
            step={1}
            value={zoomPercentage}
            onChange={handleZoomChange}
            style={{ height: '100%' }}
            styles={{
              track: {
                backgroundColor: '#3B82F6',
              },
              handle: {
                borderColor: '#3B82F6',
                backgroundColor: '#3B82F6',
                opacity: 1,
              },
              rail: {
                backgroundColor: '#4B5563',
              },
            }}
          />
        </div>

        {/* Min Zoom Indicator */}
        <div className="mt-2">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M2 6L10 6" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
      </div>
    </div>
  );
}
