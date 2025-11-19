/**
 * PageCarousel
 * Main carousel view showing 3 pages at once (left, center, right)
 * Center page is in focus and can be clicked to select/deselect
 */

import { useEffect, useState, useRef } from 'react';
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
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

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

  // Measure container size on mount and resize
  useEffect(() => {
    if (!containerRef.current) return;

    let rafId: number | null = null;

    const updateSize = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();

        // Update immediately using requestAnimationFrame for smooth updates
        if (width > 0 && height > 0) {
          setContainerSize({ width, height });
        }
      }
    };

    const handleResize = (entries: ResizeObserverEntry[]) => {
      // Cancel any pending updates
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }

      // Schedule update on next frame
      rafId = requestAnimationFrame(updateSize);
    };

    // Initial measurement
    updateSize();

    // Watch for resize - throttled to animation frames
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(containerRef.current);

    return () => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
      resizeObserver.disconnect();
    };
  }, []);

  // Calculate thumbnail widths based on container size
  // Standard letter aspect ratio: 8.5:11 = 0.773
  const PDF_ASPECT_RATIO = 8.5 / 11;

  // Calculate max widths that fit in the container
  // Layout: [btn] [side] [center] [side] [btn]
  // Allocate: 48px per button, gaps between elements
  const buttonWidth = 48;
  const gapWidth = 16;
  const totalGaps = 4; // gaps between 5 elements

  const availableWidth = containerSize.width - (2 * buttonWidth) - (totalGaps * gapWidth);
  const availableHeight = containerSize.height; // Use full container height (padding already in container)

  // Distribute width: center gets 50%, sides get 20% each (10% padding)
  const maxCenterWidth = availableWidth * 0.5;
  const maxSideWidth = availableWidth * 0.2;

  // Calculate width based on height constraint (maintaining aspect ratio)
  // Reserve space for the "Click to select" text (40px)
  const maxCenterWidthByHeight = (availableHeight - 40) * PDF_ASPECT_RATIO;
  const maxSideWidthByHeight = availableHeight * PDF_ASPECT_RATIO * 0.5; // sides are smaller

  // Use the smaller of width/height constraints
  // Default to reasonable sizes if container not measured yet
  const centerWidth = containerSize.width > 0 && containerSize.height > 0
    ? Math.max(150, Math.min(maxCenterWidth, maxCenterWidthByHeight, 500))
    : 400;
  const sideWidth = containerSize.width > 0 && containerSize.height > 0
    ? Math.max(100, Math.min(maxSideWidth, maxSideWidthByHeight, 250))
    : 200;

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
      <div ref={containerRef} className="flex-1 flex items-center justify-center p-6 overflow-hidden min-h-0" style={{ border: '3px solid green' }}>
        <div className="flex items-center justify-center gap-4 w-full h-full" style={{ border: '2px solid blue' }}>
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
            <div className="opacity-50 hover:opacity-70 cursor-pointer flex-shrink-0 flex items-center justify-center" style={{ width: `${sideWidth}px`, transition: 'opacity 200ms', border: '2px solid orange' }}>
              <PageThumbnail
                pageNumber={leftPage + 1}
                width={sideWidth}
                isSelected={selectedSet.has(leftPage)}
                onClick={() => onTogglePage(leftPage)}
              />
            </div>
          ) : (
            <div style={{ width: `${sideWidth}px`, flexShrink: 0, border: '2px solid orange' }} />
          )}

          {/* Center page (focused) */}
          <div className="flex flex-col items-center flex-shrink-0" style={{ width: `${centerWidth}px`, border: '2px solid purple' }}>
            <PageThumbnail
              pageNumber={centerPage + 1}
              width={centerWidth}
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
            <div className="opacity-50 hover:opacity-70 cursor-pointer flex-shrink-0 flex items-center justify-center" style={{ width: `${sideWidth}px`, transition: 'opacity 200ms', border: '2px solid orange' }}>
              <PageThumbnail
                pageNumber={rightPage + 1}
                width={sideWidth}
                isSelected={selectedSet.has(rightPage)}
                onClick={() => onTogglePage(rightPage)}
              />
            </div>
          ) : (
            <div style={{ width: `${sideWidth}px`, flexShrink: 0, border: '2px solid orange' }} />
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
    </div>
  );
}
