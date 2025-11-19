/**
 * PageThumbnail
 * Lightweight component for rendering single PDF pages
 * Used in both sidebar list and carousel
 */

import { useState } from 'react';
import { Page } from 'react-pdf';

interface PageThumbnailProps {
  pageNumber: number;
  width?: number;
  isSelected?: boolean;
  onClick?: (pageNumber: number) => void;
  className?: string;
}

export function PageThumbnail({
  pageNumber,
  width = 150,
  isSelected = false,
  onClick,
  className = '',
}: PageThumbnailProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [baseDimensions, setBaseDimensions] = useState<{ width: number; height: number } | null>(null);

  // Fixed high-quality render width
  const RENDER_WIDTH = 500; // Fixed render width at high quality

  console.log('[PageThumbnail] Rendering page:', pageNumber, 'width:', width);

  // Calculate the scale factor to transform rendered page to fill the desired width
  // Scale is simply: desired width / rendered width
  const displayScale = width / RENDER_WIDTH;

  // Calculate actual displayed height after transform based on PDF aspect ratio
  const displayHeight = baseDimensions
    ? (RENDER_WIDTH * baseDimensions.height / baseDimensions.width) * displayScale
    : (width * 11 / 8.5);

  return (
    <div
      className={`
        relative cursor-pointer
        ${isSelected ? 'ring-4 ring-blue-500' : 'ring-1 ring-gray-600'}
        rounded overflow-hidden bg-gray-900
        hover:ring-blue-400
        ${className}
      `}
      style={{
        width: `${width}px`,
        minWidth: `${width}px`,
        height: `${displayHeight}px`,
        transition: 'none', // Remove all transitions for instant resizing
      }}
      onClick={() => onClick?.(pageNumber)}
    >
      {/* Selection checkmark badge */}
      {isSelected && (
        <div className="absolute top-2 right-2 z-10">
          <div className="bg-blue-600 rounded-full p-1">
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-gray-800"
          style={{ aspectRatio: '8.5 / 11' }}
        >
          <p className="text-gray-500 text-xs">Loading...</p>
        </div>
      )}

      {/* PDF Page with CSS scaling */}
      <div
        style={{
          transform: `scale(${displayScale})`,
          transformOrigin: 'top left',
          width: `${RENDER_WIDTH}px`,
        }}
      >
        <Page
          pageNumber={pageNumber}
          width={RENDER_WIDTH}
          renderTextLayer={false}
          renderAnnotationLayer={false}
          onLoadSuccess={(page) => {
            console.log('[PageThumbnail] Page loaded successfully:', pageNumber);
            // Store base dimensions at scale 1.0
            const viewport = page.getViewport({ scale: 1.0 });
            setBaseDimensions({ width: viewport.width, height: viewport.height });
            setIsLoading(false);
          }}
          onLoadError={(error) => {
            console.error('[PageThumbnail] Page load error:', pageNumber, error);
          }}
          loading=""
          error={
            <div className="flex items-center justify-center h-full bg-gray-800">
              <p className="text-red-400 text-xs">Error loading page {pageNumber}</p>
            </div>
          }
        />
      </div>
    </div>
  );
}
