/**
 * PDF Feature
 * Unified exports for PDF viewing and API operations
 */

// Domain types (core PDF object types)
export type {
  BBox,
  PdfObjects,
  TextWordObject,
  TextLineObject,
  GraphicRectObject,
  GraphicLineObject,
  GraphicCurveObject,
  ImageObject,
  TableObject,
} from './types';

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
  PdfFileMetadata,
  PdfObjectsResponse,
  PdfProcessResponse,
} from './api/types';

// Components
export { PdfViewer } from './components';
export { usePdfViewer } from './components/PdfViewer/PdfViewerContext';

// Hooks
export { usePdfCoordinates } from './hooks';

// Utilities
export { createSubsetPdf } from './utils/createSubsetPdf';
