/**
 * PDF Feature
 * Unified exports for PDF viewing and API operations
 */

// API hooks and utilities
export {
  usePdfData,
  usePdfMetadata,
  usePdfObjects,
  useUploadPdf,
  useProcessPdfObjects,
  getPdfDownloadUrl,
} from './api';

// API types
export type { PdfData } from './api';
export type {
  BBox,
  PdfFileMetadata,
  PdfObjectsResponse,
  PdfProcessResponse,
  TextWordObject,
  TextLineObject,
  GraphicRectObject,
  GraphicLineObject,
  GraphicCurveObject,
  ImageObject,
  TableObject,
} from './api/types';

// Components
export { PdfViewer } from './components';
export { usePdfViewer } from './components/PdfViewer/PdfViewerContext';

// Hooks
export { usePdfCoordinates } from './hooks';
