/**
 * PdfViewerContext
 * Provides shared state for PDF viewing components including scale, pagination,
 * dimensions, and coordinate transformation functions
 */

import { createContext, useContext } from 'react';

export interface PdfDimensions {
  width: number;
  height: number;
}

export interface PdfPoint {
  x: number;
  y: number;
}

export interface PdfViewerContextValue {
  // State
  scale: number; // User's zoom level (0.5 - 3.0)
  renderScale: number; // Fixed scale PDF is rendered at (for overlay calculations)
  currentPage: number;
  numPages: number | null;
  pdfDimensions: PdfDimensions | null;
  scrollPosition: PdfPoint;

  // Actions
  setScale: (scale: number) => void;
  setCurrentPage: (page: number) => void;
  goToNextPage: () => void;
  goToPreviousPage: () => void;
  zoomIn: () => void;
  zoomOut: () => void;

  // Coordinate transformation
  pdfToScreen: (point: PdfPoint) => PdfPoint;
  screenToPdf: (point: PdfPoint) => PdfPoint;

  // Internal (used by Canvas component)
  onDocumentLoadSuccess: (numPages: number) => void;
  onPageRenderSuccess: (dimensions: PdfDimensions) => void;
}

export const PdfViewerContext = createContext<PdfViewerContextValue | null>(null);

export function usePdfViewer(): PdfViewerContextValue {
  const context = useContext(PdfViewerContext);
  if (!context) {
    throw new Error('usePdfViewer must be used within a PdfViewer component');
  }
  return context;
}
