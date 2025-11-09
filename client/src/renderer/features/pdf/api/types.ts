/**
 * PDF API Types
 * Request and response types matching the backend API
 * Imports domain types from ../types.ts
 */

import type {
  BBox,
  PdfObjects,
  TextWordObject,
  TextLineObject,
  GraphicRectObject,
  GraphicLineObject,
  GraphicCurveObject,
  ImageObject,
  TableObject,
} from '../types';

// Re-export domain types for convenience
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
};

// ============================================================================
// PDF Metadata (GET /pdf-files/{id})
// ============================================================================

export interface PdfFileMetadata {
  id: number;
  email_id: number | null;
  filename: string;
  original_filename: string;
  relative_path: string;
  file_size: number | null; // bytes
  file_hash: string | null;
  page_count: number | null;
}

// ============================================================================
// PDF Objects Response (GET /pdf-files/{id}/objects)
// ============================================================================
export interface PdfObjectsResponse {
  pdf_file_id: number;
  page_count: number;
  objects: PdfObjects;
}

// ============================================================================
// PDF Processing (POST /pdf-files/process)
// ============================================================================
export interface PdfProcessResponse {
  page_count: number;
  objects: PdfObjects;
}