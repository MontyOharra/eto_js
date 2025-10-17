/**
 * usePdfCoordinates
 * Hook for converting between PDF coordinates and screen coordinates
 * Useful for custom overlay components that need to position elements
 */

import { useCallback } from 'react';
import { usePdfViewer } from '../PdfViewer/PdfViewerContext';
import type { PdfPoint } from '../PdfViewer/PdfViewerContext';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ScreenBoundingBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

export function usePdfCoordinates() {
  const { pdfToScreen, screenToPdf, scale, pdfDimensions } = usePdfViewer();

  /**
   * Convert PDF bounding box to screen coordinates
   * PDF uses bottom-left origin, screen uses top-left origin
   */
  const pdfBboxToScreen = useCallback((bbox: BoundingBox): ScreenBoundingBox => {
    if (!pdfDimensions) {
      return { left: 0, top: 0, width: 0, height: 0 };
    }

    // PDF Y-axis starts from bottom, screen Y-axis starts from top
    const screenTopLeft = pdfToScreen({
      x: bbox.x,
      y: pdfDimensions.height - bbox.y - bbox.height,
    });

    return {
      left: screenTopLeft.x,
      top: screenTopLeft.y,
      width: bbox.width * scale,
      height: bbox.height * scale,
    };
  }, [pdfToScreen, scale, pdfDimensions]);

  /**
   * Convert screen bounding box to PDF coordinates
   */
  const screenBboxToPdf = useCallback((bbox: ScreenBoundingBox): BoundingBox => {
    if (!pdfDimensions) {
      return { x: 0, y: 0, width: 0, height: 0 };
    }

    const pdfTopLeft = screenToPdf({
      x: bbox.left,
      y: bbox.top,
    });

    return {
      x: pdfTopLeft.x,
      y: pdfDimensions.height - pdfTopLeft.y - (bbox.height / scale),
      width: bbox.width / scale,
      height: bbox.height / scale,
    };
  }, [screenToPdf, scale, pdfDimensions]);

  return {
    pdfToScreen,
    screenToPdf,
    pdfBboxToScreen,
    screenBboxToPdf,
    scale,
    pdfDimensions,
  };
}
