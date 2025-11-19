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

  console.log('[PageThumbnail] Rendering page:', pageNumber, 'width:', width);

  return (
    <div
      className={`
        relative cursor-pointer transition-all
        ${isSelected ? 'ring-4 ring-blue-500' : 'ring-1 ring-gray-600'}
        rounded overflow-hidden bg-gray-900
        hover:ring-blue-400
        ${className}
      `}
      style={{
        width: `${width}px`,
        minWidth: `${width}px`,
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
          style={{ width, aspectRatio: '8.5 / 11' }}
        >
          <p className="text-gray-500 text-xs">Loading...</p>
        </div>
      )}

      {/* PDF Page */}
      <Page
        pageNumber={pageNumber}
        width={width}
        renderTextLayer={false}
        renderAnnotationLayer={false}
        onLoadSuccess={(page) => {
          console.log('[PageThumbnail] Page loaded successfully:', pageNumber);
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
  );
}
