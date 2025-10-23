/**
 * PDF Files API Types (DTOs)
 * Request and response types matching the backend API
 */

// ============================================================================
// BBox Type (used across all object types)
// ============================================================================

export type BBox = [number, number, number, number]; // [x0, y0, x1, y1]

// ============================================================================
// PDF Metadata (GET /pdf-files/{id})
// ============================================================================

export interface PdfFileMetadataDTO {
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
// PDF Objects (GET /pdf-files/{id}/objects)
// ============================================================================

export interface TextWordObjectDTO {
  page: number;
  bbox: BBox;
  text: string;
  fontname: string;
  fontsize: number;
}

export interface TextLineObjectDTO {
  page: number;
  bbox: BBox;
}

export interface GraphicRectObjectDTO {
  page: number;
  bbox: BBox;
  linewidth: number;
}

export interface GraphicLineObjectDTO {
  page: number;
  bbox: BBox;
  linewidth: number;
}

export interface GraphicCurveObjectDTO {
  page: number;
  bbox: BBox;
  points: [number, number][]; // Array of [x, y] coordinate pairs
  linewidth: number;
}

export interface ImageObjectDTO {
  page: number;
  bbox: BBox;
  format: string; // e.g., "JPEG", "PNG"
  colorspace: string; // e.g., "RGB", "CMYK"
  bits: number; // Bit depth
}

export interface TableObjectDTO {
  page: number;
  bbox: BBox;
  rows: number;
  cols: number;
}

export interface PdfObjectsResponseDTO {
  pdf_file_id: number;
  page_count: number;
  objects: {
    text_words: TextWordObjectDTO[];
    text_lines: TextLineObjectDTO[];
    graphic_rects: GraphicRectObjectDTO[];
    graphic_lines: GraphicLineObjectDTO[];
    graphic_curves: GraphicCurveObjectDTO[];
    images: ImageObjectDTO[];
    tables: TableObjectDTO[];
  };
}

// ============================================================================
// PDF Processing (POST /pdf-files/process)
// ============================================================================

// Response for processing uploaded PDFs (no pdf_file_id since not stored)
export interface PdfProcessResponseDTO {
  page_count: number;
  objects: {
    text_words: TextWordObjectDTO[];
    text_lines: TextLineObjectDTO[];
    graphic_rects: GraphicRectObjectDTO[];
    graphic_lines: GraphicLineObjectDTO[];
    graphic_curves: GraphicCurveObjectDTO[];
    images: ImageObjectDTO[];
    tables: TableObjectDTO[];
  };
}

// ============================================================================
// PDF Download (GET /pdf-files/{id}/download)
// ============================================================================

// Note: Download endpoint returns raw PDF bytes with headers:
// - Content-Type: application/pdf
// - Content-Disposition: inline; filename="<original_filename>"
// Frontend handles as Blob/ArrayBuffer for PDF.js or iframe embedding
