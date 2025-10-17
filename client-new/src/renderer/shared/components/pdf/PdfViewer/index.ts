/**
 * PdfViewer - Compound Component for PDF Viewing
 *
 * Usage:
 * <PdfViewer pdfUrl={url}>
 *   <PdfViewer.Canvas pdfUrl={url} />
 *   <PdfViewer.Controls position="bottom-center" />
 *   <PdfViewer.InfoPanel position="top-right" filename="doc.pdf" fileSize={1024000} />
 *   <PdfViewer.Overlay>
 *     // Custom overlay components
 *   </PdfViewer.Overlay>
 * </PdfViewer>
 */

export { PdfViewer } from './PdfViewer';
export { PdfCanvas } from './PdfCanvas';
export { PdfOverlay } from './PdfOverlay';
export { PdfControls } from './PdfControls';
export { PdfInfoPanel } from './PdfInfoPanel';
export { usePdfViewer } from './PdfViewerContext';
export type {
  PdfViewerProps,
} from './PdfViewer';
export type {
  PdfViewerContextValue,
  PdfDimensions,
  PdfPoint,
} from './PdfViewerContext';
