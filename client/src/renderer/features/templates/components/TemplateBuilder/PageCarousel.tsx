/**
 * PageCarousel
 * Main carousel view showing 3 pages at once (left, center, right)
 * Center page is in focus and can be clicked to select/deselect
 */

import { useEffect } from 'react';
import { PageThumbnail } from './PageThumbnail';

interface PageCarouselProps {
  totalPages: number;
  selectedPages: number[];
  onTogglePage: (pageIndex: number) => void;
  focusedPageIndex: number;
  onFocusChange: (pageIndex: number) => void;
}

export function PageCarousel({
  totalPages,
  selectedPages,
  onTogglePage,
  focusedPageIndex,
  onFocusChange,
}: PageCarouselProps) {
  const selectedSet = new Set(selectedPages);

  const canGoPrev = focusedPageIndex > 0;
  const canGoNext = focusedPageIndex < totalPages - 1;

  const handlePrev = () => {
    if (canGoPrev) {
      onFocusChange(focusedPageIndex - 1);
    }
  };

  const handleNext = () => {
    if (canGoNext) {
      onFocusChange(focusedPageIndex + 1);
    }
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        handlePrev();
      } else if (e.key === 'ArrowRight') {
        handleNext();
      } else if (e.key === ' ') {
        e.preventDefault();
        onTogglePage(focusedPageIndex);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [focusedPageIndex, totalPages]);

  // Calculate which pages to show (left, center, right)
  const centerPage = focusedPageIndex;
  const leftPage = centerPage > 0 ? centerPage - 1 : null;
  const rightPage = centerPage < totalPages - 1 ? centerPage + 1 : null;

  return (
    <div className="flex-1 flex flex-col bg-gray-800 h-full overflow-hidden">
      {/* Page counter - Fixed height */}
      <div className="p-3 border-b border-gray-700 text-center flex-shrink-0 h-16 flex flex-col items-center justify-center">
        <p className="text-gray-300 text-sm font-medium">
          Page {focusedPageIndex + 1} of {totalPages}
          {selectedSet.has(focusedPageIndex) && (
            <span className="ml-2 text-blue-400 text-xs">✓ Selected</span>
          )}
        </p>
      </div>

      {/* Carousel container - Flexible height */}
      <div className="flex-1 flex items-center justify-center p-6 overflow-hidden min-h-0">
        <div className="flex items-center justify-center gap-4 max-h-full">
          {/* Left navigation button */}
          <button
            onClick={handlePrev}
            disabled={!canGoPrev}
            className="p-3 rounded-full bg-gray-700 hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            aria-label="Previous page"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          {/* Left page (preview or placeholder) */}
          {leftPage !== null ? (
            <div className="opacity-50 hover:opacity-70 transition-opacity cursor-pointer">
              <PageThumbnail
                pageNumber={leftPage + 1}
                width={250}
                isSelected={selectedSet.has(leftPage)}
                onClick={() => onTogglePage(leftPage)}
              />
            </div>
          ) : (
            <div style={{ width: '250px', minWidth: '250px' }} />
          )}

          {/* Center page (focused) */}
          <div className="flex flex-col items-center">
            <PageThumbnail
              pageNumber={centerPage + 1}
              width={500}
              isSelected={selectedSet.has(centerPage)}
              onClick={() => onTogglePage(centerPage)}
              className="shadow-2xl"
            />
            <p className="text-center text-gray-300 text-sm mt-3 font-medium">
              Click to {selectedSet.has(centerPage) ? 'deselect' : 'select'}
            </p>
          </div>

          {/* Right page (preview or placeholder) */}
          {rightPage !== null ? (
            <div className="opacity-50 hover:opacity-70 transition-opacity cursor-pointer">
              <PageThumbnail
                pageNumber={rightPage + 1}
                width={250}
                isSelected={selectedSet.has(rightPage)}
                onClick={() => onTogglePage(rightPage)}
              />
            </div>
          ) : (
            <div style={{ width: '250px', minWidth: '250px' }} />
          )}

          {/* Right navigation button */}
          <button
            onClick={handleNext}
            disabled={!canGoNext}
            className="p-3 rounded-full bg-gray-700 hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            aria-label="Next page"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Keyboard hint - Fixed height */}
      <div className="p-3 border-t border-gray-700 text-center flex-shrink-0 h-12 flex items-center justify-center">
        <p className="text-gray-400 text-xs">
          Use <kbd className="px-1.5 py-0.5 bg-gray-700 rounded text-gray-300">←</kbd>{' '}
          <kbd className="px-1.5 py-0.5 bg-gray-700 rounded text-gray-300">→</kbd> to navigate
          {' • '}
          <kbd className="px-1.5 py-0.5 bg-gray-700 rounded text-gray-300">Space</kbd> to select
        </p>
      </div>
    </div>
  );
}
