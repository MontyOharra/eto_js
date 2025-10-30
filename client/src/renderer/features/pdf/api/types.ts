/**
 * PDF API Types (s)
 * Request and response types matching the backend API
 */

// ============================================================================
// BBox Type (used across all object types)
// ============================================================================

export type BBox = [number, number, number, number]; // [x0, y0, x1, y1]

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
// PDF Objects (GET /pdf-files/{id}/objects)
// ============================================================================

export interface TextWordObject {
  page: number;
  bbox: BBox;
  text: string;
  fontname: string;
  fontsize: number;
}

export interface TextLineObject {
  page: number;
  bbox: BBox;
}

export interface GraphicRectObject {
  page: number;
  bbox: BBox;
  linewidth: number;
}

export interface GraphicLineObject {
  page: number;
  bbox: BBox;
  linewidth: number;
}

export interface GraphicCurveObject {
  page: number;
  bbox: BBox;
  points: [number, number][]; // Array of [x, y] coordinate pairs
  linewidth: number;
}

export interface ImageObject {
  page: number;
  bbox: BBox;
  format: string; // e.g., "JPEG", "PNG"
  colorspace: string; // e.g., "RGB", "CMYK"
  bits: number; // Bit depth
}

export interface TableObject {
  page: number;
  bbox: BBox;
  rows: number;
  cols: number;
}

export interface PdfObjects {
  text_words: TextWordObject[];
  text_lines: TextLineObject[];
  graphic_rects: GraphicRectObject[];
  graphic_lines: GraphicLineObject[];
  graphic_curves: GraphicCurveObject[];
  images: ImageObject[];
  tables: TableObject[];
}

// ============================================================================
// PDF Processing (GET /pdf-files/{id}/objects)
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