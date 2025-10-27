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
  field_id: string; // unique identifier
  label: string; // e.g., "hawb", "customer_name"
  description: string | null;
  page: number;
  bbox: BBox;
  required: boolean;
  validation_regex: string | null;
}

// Note: PipelineState and VisualState are now imported from the canonical location
// Import from: '../../../types/pipelineTypes'
// This avoids schema duplication and ensures consistency with the pipeline system

export interface TemplateVersion {
  version_id: number;
  version_num: number;
  usage_count: number;
  last_used_at: string | null; // ISO 8601
  signature_objects: SignatureObject[];
  extraction_fields: ExtractionField[];
  pipeline_definition_id: number;
}

export interface TemplateVersionDetail extends TemplateVersion {
  template_id: number;
  is_current: boolean; // true if this is template's current_version_id
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
// Detail View
// =============================================================================

export interface TemplateDetail {
  // Template metadata
  id: number;
  name: string;
  description: string | null;
  source_pdf_id: number;
  status: TemplateStatus;
  current_version_id: number;

  // Current version details (denormalized for convenience)
  current_version: TemplateVersion;

  // Version history summary
  total_versions: number;
}

// =============================================================================
// Version Summary (for version list)
// =============================================================================

export interface TemplateVersionListItem {
  version_id: number;
  version_num: number;
  usage_count: number; // ETO runs that used this version
  last_used_at: string | null; // ISO 8601
  is_current: boolean; // true if this is current_version_id
}
