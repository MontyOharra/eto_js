/**
 * PdfOverlay
 * Container for overlay elements that need to align with PDF coordinates
 * Provides coordinate transformation and maintains alignment during zoom/scroll
 */

import { ReactNode } from 'react';
import { usePdfViewer } from './PdfViewerContext';

export interface PdfOverlayProps {
  children: ReactNode;
  className?: string;
}

export function PdfOverlay({ children, className = '' }: PdfOverlayProps) {
  const { scale, pdfDimensions } = usePdfViewer();

  if (!pdfDimensions) {
    // PDF not loaded yet, don't render overlay
    return null;
  }

  // Calculate scaled dimensions
  const scaledWidth = pdfDimensions.width * scale;
  const scaledHeight = pdfDimensions.height * scale;

  return (
    <div
      className={`absolute top-0 left-0 ${className}`}
      style={{
        width: scaledWidth,
        height: scaledHeight,
        pointerEvents: 'none', // Allow clicks to pass through to PDF by default
      }}
    >
      {/* Container for overlay children */}
      <div className="relative w-full h-full">
        {children}
      </div>
    </div>
  );
}
