// Domain types for Templates feature

export type TemplateStatus = 'active' | 'inactive';

export type PdfObjectType =
  | 'text_word'
  | 'text_line'
  | 'graphic_rect'
  | 'graphic_line'
  | 'graphic_curve'
  | 'image'
  | 'table';

export type BBox = [number, number, number, number]; // [x0, y0, x1, y1]

// =============================================================================
// Nested Types
// =============================================================================

export interface TemplateVersionSummary {
  version_id: number;
  version_num: number;
  usage_count: number; // ETO runs that used this version
}

// Version identifier for navigation (lightweight)
export interface VersionListItem {
  version_id: number;
  version_number: number;
}

// PdfObjects format (matches backend storage)
export interface PdfObjects {
  text_words: Array<{
    type: 'text_word';
    page: number;
    bbox: BBox;
    text: string;
    fontname?: string;
    fontsize?: number;
  }>;
  text_lines: Array<{
    type: 'text_line';
    page: number;
    bbox: BBox;
    text?: string;
  }>;
  graphic_rects: Array<{
    type: 'graphic_rect';
    page: number;
    bbox: BBox;
    linewidth?: number;
  }>;
  graphic_lines: Array<{
    type: 'graphic_line';
    page: number;
    bbox: BBox;
    linewidth?: number;
  }>;
  graphic_curves: Array<{
    type: 'graphic_curve';
    page: number;
    bbox: BBox;
    points?: Array<[number, number]>;
    linewidth?: number;
  }>;
  images: Array<{
    type: 'image';
    page: number;
    bbox: BBox;
    format: string;
    colorspace: string;
    bits: number;
  }>;
  tables: Array<{
    type: 'table';
    page: number;
    bbox: BBox;
    rows: number;
    cols: number;
  }>;
}

// Legacy SignatureObject type - kept for backward compatibility but deprecated
// Use PdfObjects instead
export interface SignatureObject {
  object_type: PdfObjectType;
  page: number;
  bbox: BBox;
  // Additional properties vary by object_type (matching PDF extraction)
  text?: string;
  fontname?: string;
  fontsize?: number;
  linewidth?: number;
  points?: Array<[number, number]>;
  format?: string;
  colorspace?: string;
  bits?: number;
  rows?: number;
  cols?: number;
}

export interface ExtractionField {
  name: string; // unique identifier - e.g., "hawb", "customer_name"
  description: string | null;
  page: number; // 1-indexed (page 1 = first page)
  bbox: BBox;
}

// Note: PipelineState and VisualState are now imported from the canonical location
// Import from: '../../../types/pipelineTypes'
// This avoids schema duplication and ensures consistency with the pipeline system

export interface TemplateVersion {
  version_id: number;
  version_num: number;
  source_pdf_id: number;
  is_current: boolean;
  signature_objects: PdfObjects; // Uses PdfObjects format (not flat array)
  extraction_fields: ExtractionField[];
  pipeline_definition_id: number;
}

export interface TemplateVersionDetail extends TemplateVersion {
  template_id: number;
}

// =============================================================================
// List/Summary View
// =============================================================================

export interface TemplateListItem {
  id: number;
  name: string;
  description: string | null;
  status: TemplateStatus;
  source_pdf_id: number;
  current_version: TemplateVersionSummary;
  total_versions: number; // Count of all versions for this template
}

// =============================================================================
// Detail View (matches backend PdfTemplate)
// =============================================================================

export interface TemplateDetail {
  id: number;
  name: string;
  description: string | null;
  status: TemplateStatus;
  source_pdf_id: number;
  current_version_id: number | null;
  versions: VersionListItem[]; // All versions for navigation (IDs + numbers only)
}
