/**
 * Pipelines & Modules API Types (DTOs)
 * Request and response types matching the backend API
 */

// ============================================================================
// Module Catalog Types (GET /modules)
// ============================================================================

export type ModuleKind = 'transform' | 'action' | 'logic' | 'entry_point';

export interface ModuleInputDTO {
  id: string;
  name: string;
  type: string[]; // Allowed types (e.g., ["string", "number"])
  required: boolean;
  description: string;
}

export interface ModuleOutputDTO {
  id: string;
  name: string;
  type: string[]; // Output types
  description: string;
}

export interface ModuleMetaDTO {
  inputs: ModuleInputDTO[];
  outputs: ModuleOutputDTO[];
  // Future: additional metadata fields
}

export interface ModuleCatalogItemDTO {
  id: string; // Module identifier
  version: string; // Module version (e.g., "1.0.0")
  name: string; // Display name
  description: string; // User-facing description
  color: string; // UI display color (hex code)
  category: string; // e.g., "Text Processing", "Actions", "Logic"
  module_kind: ModuleKind;
  meta: ModuleMetaDTO;
  config_schema: object; // JSON Schema for configuration UI
}

export interface ModulesQueryParams {
  module_kind?: ModuleKind;
  category?: string;
  search?: string;
}

// ============================================================================
// Pipeline State Types (logical structure)
// ============================================================================

export interface EntryPointDTO {
  id: string;
  label: string;
  field_reference: string; // For templates, references extraction field label
}

export interface NodeDTO {
  node_id: string;
  name: string;
  type: string[];
}

export interface ModuleInstanceDTO {
  instance_id: string;
  module_id: string; // Reference to module_catalog
  config: object; // Module-specific configuration
  inputs: NodeDTO[];
  outputs: NodeDTO[];
}

export interface ConnectionDTO {
  from_node_id: string; // Entry point or module output node
  to_node_id: string; // Module input node
}

export interface PipelineStateDTO {
  entry_points: EntryPointDTO[];
  modules: ModuleInstanceDTO[];
  connections: ConnectionDTO[];
}

// ============================================================================
// Visual State Types (UI layout)
// ============================================================================

export interface PositionDTO {
  x: number;
  y: number;
}

export interface VisualStateDTO {
  positions: Record<string, PositionDTO>; // entry_point_id or module_instance_id → position
}

// ============================================================================
// Pipeline Definition Types
// ============================================================================

export interface PipelineSummaryDTO {
  id: number;
  compiled_plan_id: number | null; // null if not yet compiled
  created_at: string; // ISO 8601 (dev/testing only)
  updated_at: string; // ISO 8601 (dev/testing only)
}

export interface PipelinesListResponseDTO {
  items: PipelineSummaryDTO[];
  total: number;
  limit: number;
  offset: number;
}

export interface PipelineDetailDTO {
  id: number;
  compiled_plan_id: number | null;
  pipeline_state: PipelineStateDTO;
  visual_state: VisualStateDTO;
}

// ============================================================================
// Create/Update Requests
// ============================================================================

export interface CreatePipelineRequestDTO {
  pipeline_state: PipelineStateDTO;
  visual_state: VisualStateDTO;
}

export interface CreatePipelineResponseDTO {
  id: number; // Created pipeline ID
  compiled_plan_id: number | null; // null initially, set on first compilation
}

export interface UpdatePipelineRequestDTO {
  pipeline_state: PipelineStateDTO;
  visual_state: VisualStateDTO;
}

export interface UpdatePipelineResponseDTO {
  id: number;
  compiled_plan_id: number | null; // May change if pipeline logic changed
}

// ============================================================================
// Validation
// ============================================================================

export interface ValidationErrorDTO {
  code: string; // Error code (e.g., "type_mismatch", "cycle_detected")
  message: string; // Human-readable error message
  where?: Record<string, any> | null; // Additional context (connection, module, etc.)
}

export interface ValidatePipelineRequestDTO {
  pipeline_json: PipelineStateDTO;
}

export interface ValidatePipelineResponseDTO {
  valid: boolean;
  errors: ValidationErrorDTO[];
}

// ============================================================================
// Query Parameters
// ============================================================================

export interface PipelinesQueryParams {
  sort_by?: 'id' | 'created_at';
  sort_order?: 'asc' | 'desc';
  limit?: number; // default: 50, max: 200
  offset?: number; // default: 0
}
