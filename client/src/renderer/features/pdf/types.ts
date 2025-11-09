/**
 * PDF Domain Types
 * Represents the structure of PDF objects extracted from PDF files
 * These types match the backend domain types and are used across features
 */

// ============================================================================
// BBox Type (used across all object types)
// ============================================================================

export type BBox = [number, number, number, number]; // [x0, y0, x1, y1]

// ============================================================================
// PDF Object Types
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

/**
 * Complete PDF objects structure
 * Contains all extracted objects from a PDF file, organized by type
 * Matches backend: server/src/api/schemas/pdf_files.py::PdfObjects
 */
export interface PdfObjects {
  text_words: TextWordObject[];
  text_lines: TextLineObject[];
  graphic_rects: GraphicRectObject[];
  graphic_lines: GraphicLineObject[];
  graphic_curves: GraphicCurveObject[];
  images: ImageObject[];
  tables: TableObject[];
}
