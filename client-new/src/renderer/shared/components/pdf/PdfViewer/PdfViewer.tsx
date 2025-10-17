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

import { useState, useCallback, ReactNode } from 'react';
import { pdfjs } from 'react-pdf';
import {
  PdfViewerContext,
  PdfDimensions,
  PdfPoint,
  PdfViewerContextValue
} from './PdfViewerContext';
import { PdfCanvas } from './PdfCanvas';
import { PdfOverlay } from './PdfOverlay';
import { PdfControls } from './PdfControls';
import { PdfInfoPanel } from './PdfInfoPanel';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

export interface PdfViewerProps {
  pdfUrl: string;
  initialScale?: number;
  minScale?: number;
  maxScale?: number;
  scaleStep?: number;
  /**
   * Children should include PdfViewer.Canvas with any overlays as children of Canvas.
   * See component documentation above for proper overlay scaling/positioning.
   */
  children: ReactNode;
  onError?: (error: Error) => void;
}

export function PdfViewer({
  pdfUrl,
  initialScale = 1.0,
  minScale = 0.5,
  maxScale = 2.0,
  scaleStep = 0.25,
  children,
  onError,
}: PdfViewerProps) {
  // State
  const [scale, setScaleState] = useState(initialScale);
  const [currentPage, setCurrentPage] = useState(1);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pdfDimensions, setPdfDimensions] = useState<PdfDimensions | null>(null);
  const [scrollPosition] = useState<PdfPoint>({ x: 0, y: 0 });

  // Scale control with bounds
  const setScale = useCallback((newScale: number) => {
    setScaleState(Math.max(minScale, Math.min(maxScale, newScale)));
  }, [minScale, maxScale]);

  // Page navigation
  const goToNextPage = useCallback(() => {
    if (numPages) {
      setCurrentPage(prev => Math.min(numPages, prev + 1));
    }
  }, [numPages]);

  const goToPreviousPage = useCallback(() => {
    setCurrentPage(prev => Math.max(1, prev - 1));
  }, []);

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

  // Callbacks for Canvas component
  const onDocumentLoadSuccess = useCallback((loadedNumPages: number) => {
    setNumPages(loadedNumPages);
    setCurrentPage(1); // Reset to first page
  }, []);

  const onPageRenderSuccess = useCallback((dimensions: PdfDimensions) => {
    setPdfDimensions(dimensions);
  }, []);

  // Context value
  const contextValue: PdfViewerContextValue = {
    scale,
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
    pdfToScreen,
    screenToPdf,
    onDocumentLoadSuccess,
    onPageRenderSuccess,
  };

  return (
    <PdfViewerContext.Provider value={contextValue}>
      <div className="relative w-full h-full flex flex-col p-4">
        {children}
      </div>
    </PdfViewerContext.Provider>
  );
}

// Compound component exports
PdfViewer.Canvas = PdfCanvas;
PdfViewer.Overlay = PdfOverlay;
PdfViewer.Controls = PdfControls;
PdfViewer.InfoPanel = PdfInfoPanel;
