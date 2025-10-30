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
  PdfFileMetadataDTO,
  PdfObjectsResponseDTO,
  PdfProcessResponseDTO,
  TextWordObjectDTO,
  TextLineObjectDTO,
  GraphicRectObjectDTO,
  GraphicLineObjectDTO,
  GraphicCurveObjectDTO,
  ImageObjectDTO,
  TableObjectDTO,
} from './api/types';

// Components
export { PdfViewer } from './components';
export { usePdfViewer } from './components/PdfViewer/PdfViewerContext';

// Hooks
export { usePdfCoordinates } from './hooks';
