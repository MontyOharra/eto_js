/**
 * PdfViewer - Compound Component for PDF Viewing
 *
 * Usage:
 * <PdfViewer pdfUrl={url}>
 *   <PdfViewer.Canvas pdfUrl={url}>
 *     // Custom overlay components
 *   </PdfViewer.Canvas>
 *   <PdfViewer.ControlsSidebar position="right" />
 * </PdfViewer>
 */

export { PdfViewer } from './PdfViewer';
export { PdfCanvas } from './PdfCanvas';
export { PdfOverlay } from './PdfOverlay';
export { PdfControlsSidebar } from './PdfControlsSidebar';
export { usePdfViewer } from './PdfViewerContext';
export type {
  PdfViewerProps,
} from './PdfViewer';
export type {
  PdfViewerContextValue,
  PdfDimensions,
  PdfPoint,
} from './PdfViewerContext';
