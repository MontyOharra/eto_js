/**
 * PdfViewer - Main Component
 * Container component that provides context and manages PDF viewer state
 *
 * IMPORTANT: Overlay Scaling and Positioning
 * ------------------------------------------
 * The `pdfDimensions` provided in context are CONSTANT and represent the PDF's
 * base size at scale 1.0. They do NOT change when the user zooms.
 *
 * To create overlays that properly scale and pan with the PDF:
 *
 * 1. Pass overlay elements as children to PdfViewer.Canvas (NOT as siblings)
 * 2. Use absolute positioning with pixel values calculated as: baseDimension * scale
 * 3. Access scale and pdfDimensions via usePdfViewer() hook
 *
 * Example - Correct Usage:
 * ```tsx
 * function MyOverlay() {
 *   const { scale, pdfDimensions } = usePdfViewer();
 *   if (!pdfDimensions) return null;
 *
 *   // Calculate position/size: base value * scale
 *   const boxSize = 100; // 100 PDF points (constant)
 *
 *   return (
 *     <div style={{
 *       position: 'absolute',
 *       left: `${20 * scale}px`,        // 20 points from left, scales with zoom
 *       top: `${20 * scale}px`,         // 20 points from top, scales with zoom
 *       width: `${boxSize * scale}px`,  // Scales proportionally
 *       height: `${boxSize * scale}px`,
 *     }}>
 *       Content
 *     </div>
 *   );
 * }
 *
 * // Usage:
 * <PdfViewer pdfUrl={url}>
 *   <PdfViewer.Canvas pdfUrl={url}>
 *     <MyOverlay />
 *   </PdfViewer.Canvas>
 *   <PdfViewer.Controls />
 * </PdfViewer>
 * ```
 *
 * Why This Works:
 * - pdfDimensions.width and pdfDimensions.height are CONSTANT (from scale 1.0)
 * - Multiplying by current scale gives correct screen pixel size
 * - Overlays are positioned inside Canvas's scrollable/zoomable container
 * - Result: Overlays stay perfectly aligned during zoom and scroll
 */

import { useState, useCallback, useEffect, ReactNode } from 'react';
import { pdfjs } from 'react-pdf';
import {
  PdfViewerContext,
  PdfDimensions,
  PdfPoint,
  PdfViewerContextValue
} from './PdfViewerContext';
import { PdfCanvas } from './PdfCanvas';
import { PdfOverlay } from './PdfOverlay';
import { PdfControlsSidebar } from './PdfControlsSidebar';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

export interface PdfViewerProps {
  pdfUrl: string;
  initialScale?: number;
  initialPage?: number;
  minScale?: number;
  maxScale?: number;
  scaleStep?: number;
  /**
   * Children should include PdfViewer.Canvas with any overlays as children of Canvas.
   * See component documentation above for proper overlay scaling/positioning.
   */
  children: ReactNode;
  onError?: (error: Error) => void;
  /** Callback when scale changes (for controlled state) */
  onScaleChange?: (scale: number) => void;
  /** Callback when page changes (for controlled state) */
  onPageChange?: (page: number) => void;
}

export function PdfViewer({
  pdfUrl,
  initialScale = 1.0,
  initialPage = 1,
  minScale = 0.5,
  maxScale = 3.0,
  scaleStep = 0.25,
  children,
  onError,
  onScaleChange,
  onPageChange,
}: PdfViewerProps) {
  // State
  const [scale, setScaleState] = useState(initialScale);
  const [currentPage, setCurrentPageState] = useState(initialPage);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pdfDimensions, setPdfDimensions] = useState<PdfDimensions | null>(null);
  const [scrollPosition] = useState<PdfPoint>({ x: 0, y: 0 });

  // Fixed high-quality render scale (matches PdfCanvas)
  const RENDER_SCALE = 3.0;

  // Sync with external state (controlled component)
  useEffect(() => {
    if (initialScale !== scale) {
      setScaleState(initialScale);
    }
  }, [initialScale]);

  useEffect(() => {
    if (initialPage !== currentPage) {
      setCurrentPageState(initialPage);
    }
  }, [initialPage]);

  // Scale control with bounds
  const setScale = useCallback((newScale: number) => {
    const clampedScale = Math.max(minScale, Math.min(maxScale, newScale));
    setScaleState(clampedScale);
    onScaleChange?.(clampedScale);
  }, [minScale, maxScale, onScaleChange]);

  const setCurrentPage = useCallback((newPage: number) => {
    setCurrentPageState(newPage);
    onPageChange?.(newPage);
  }, [onPageChange]);

  // Page navigation
  const goToNextPage = useCallback(() => {
    if (numPages && currentPage < numPages) {
      setCurrentPage(currentPage + 1);
    }
  }, [numPages, currentPage, setCurrentPage]);

  const goToPreviousPage = useCallback(() => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  }, [currentPage, setCurrentPage]);

  // Zoom controls
  const zoomIn = useCallback(() => {
    setScale(scale + scaleStep);
  }, [scale, scaleStep, setScale]);

  const zoomOut = useCallback(() => {
    setScale(scale - scaleStep);
  }, [scale, scaleStep, setScale]);

  // Coordinate transformation
  const pdfToScreen = useCallback((point: PdfPoint): PdfPoint => {
    if (!pdfDimensions) return { x: 0, y: 0 };
    return {
      x: point.x * scale,
      y: point.y * scale,
    };
  }, [scale, pdfDimensions]);

  const screenToPdf = useCallback((point: PdfPoint): PdfPoint => {
    if (!pdfDimensions) return { x: 0, y: 0 };
    return {
      x: point.x / scale,
      y: point.y / scale,
    };
  }, [scale, pdfDimensions]);

  // Fit PDF to width
  const fitToWidth = useCallback((containerWidth: number, sidebarWidth: number) => {
    console.log('[fitToWidth] Called with:', { containerWidth, sidebarWidth, pdfDimensions });
    if (!pdfDimensions) {
      console.log('[fitToWidth] No PDF dimensions, returning');
      return;
    }

    // Calculate available width for PDF (container width - sidebar width - padding)
    const padding = 32; // px-4 on PdfCanvas = 16px on each side
    const availableWidth = containerWidth - sidebarWidth - padding;
    console.log('[fitToWidth] Available width:', availableWidth);

    // Calculate scale to fit PDF width
    const newScale = availableWidth / pdfDimensions.width;
    console.log('[fitToWidth] Calculated scale:', newScale);

    // Clamp to min/max zoom
    const clampedScale = Math.max(minScale, Math.min(maxScale, newScale));
    console.log('[fitToWidth] Clamped scale:', clampedScale);
    setScale(clampedScale);
  }, [pdfDimensions, minScale, maxScale, setScale]);

  // Callbacks for Canvas component
  const onDocumentLoadSuccess = useCallback((loadedNumPages: number) => {
    setNumPages(loadedNumPages);
    // Don't reset to first page - preserve user's current page
  }, []);

  const onPageRenderSuccess = useCallback((dimensions: PdfDimensions) => {
    setPdfDimensions(dimensions);
  }, []);

  // Context value
  const contextValue: PdfViewerContextValue = {
    scale,
    renderScale: RENDER_SCALE, // Fixed render scale for overlay calculations
    currentPage,
    numPages,
    pdfDimensions,
    scrollPosition,
    setScale,
    setCurrentPage,
    goToNextPage,
    goToPreviousPage,
    zoomIn,
    zoomOut,
    fitToWidth,
    pdfToScreen,
    screenToPdf,
    onDocumentLoadSuccess,
    onPageRenderSuccess,
  };

  return (
    <PdfViewerContext.Provider value={contextValue}>
      <div className="relative w-full h-full flex">
        {children}
      </div>
    </PdfViewerContext.Provider>
  );
}

// Compound component exports
PdfViewer.Canvas = PdfCanvas;
PdfViewer.Overlay = PdfOverlay;
PdfViewer.ControlsSidebar = PdfControlsSidebar;
