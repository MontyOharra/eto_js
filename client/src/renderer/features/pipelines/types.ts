// Domain types for Pipelines feature
// Note: Pipelines are dev/testing only - no name/description/status
// In production, pipelines are embedded in PDF templates

// =============================================================================
// List/Summary View (matches GET /pipelines backend response)
// =============================================================================

export interface PipelineListItem {
  id: number;
  compiled_plan_id: number | null;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

// =============================================================================
// Detail View (matches GET /pipelines/{id} backend response)
// =============================================================================

export interface PipelineDetail extends PipelineListItem {
  // Pipeline state (logical structure)
  pipeline_state: {
    entry_points: Array<{
      node_id: string;
      name: string;
    }>;
    modules: Array<{
      module_instance_id: string;
      module_ref: string; // e.g., "trim_text:1.0.0"
      module_kind: string; // "transform" | "action" | "logic"
      config: Record<string, any>;
      inputs: Array<{
        node_id: string;
        name: string;
        type: string;
        position_index: number;
        group_index: number;
      }>;
      outputs: Array<{
        node_id: string;
        name: string;
        type: string;
        position_index: number;
        group_index: number;
      }>;
    }>;
    connections: Array<{
      from_node_id: string;
      to_node_id: string;
    }>;
  };
  // Visual state (UI positioning)
  visual_state: {
    modules: Record<string, { x: number; y: number }>;
    entryPoints?: Record<string, { x: number; y: number }>;
  };
}

// =============================================================================
// API Response Types (matches backend API_ENDPOINTS.md)
// =============================================================================

export interface PipelinesListResponse {
  items: PipelineListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface PipelineDetailResponse extends PipelineDetail {}

// =============================================================================
// API Request Types (matches POST /pipelines backend)
// =============================================================================

export interface CreatePipelineRequest {
  pipeline_state: {
    entry_points: Array<{
      node_id: string;
      name: string;
    }>;
    modules: Array<{
      module_instance_id: string;
      module_ref: string;
      module_kind: string;
      config: Record<string, any>;
      inputs: Array<{
        node_id: string;
        name: string;
        type: string;
        position_index: number;
        group_index: number;
      }>;
      outputs: Array<{
        node_id: string;
        name: string;
        type: string;
        position_index: number;
        group_index: number;
      }>;
    }>;
    connections: Array<{
      from_node_id: string;
      to_node_id: string;
    }>;
  };
  visual_state: {
    modules: Record<string, { x: number; y: number }>;
    entryPoints?: Record<string, { x: number; y: number }>;
  };
}

export interface CreatePipelineResponse {
  id: number;
  compiled_plan_id: number | null;
}

export interface UpdatePipelineRequest {
  pipeline_state: {
    entry_points: Array<{
      node_id: string;
      name: string;
    }>;
    modules: Array<{
      module_instance_id: string;
      module_ref: string;
      module_kind: string;
      config: Record<string, any>;
      inputs: Array<{
        node_id: string;
        name: string;
        type: string;
        position_index: number;
        group_index: number;
      }>;
      outputs: Array<{
        node_id: string;
        name: string;
        type: string;
        position_index: number;
        group_index: number;
      }>;
    }>;
    connections: Array<{
      from_node_id: string;
      to_node_id: string;
    }>;
  };
  visual_state: {
    modules: Record<string, { x: number; y: number }>;
    entryPoints?: Record<string, { x: number; y: number }>;
  };
}

export interface UpdatePipelineResponse {
  id: number;
  compiled_plan_id: number | null;
}

// =============================================================================
// Validation Types (matches POST /pipelines/validate backend)
// =============================================================================

export interface ValidationError {
  code: string; // Error code (e.g., "type_mismatch", "cycle_detected")
  message: string; // Human-readable error message
  where?: Record<string, any> | null; // Additional context (connection, module, etc.)
}

export interface ValidatePipelineRequest {
  pipeline_json: {
    entry_points: Array<{
      node_id: string;
      name: string;
    }>;
    modules: Array<{
      module_instance_id: string;
      module_ref: string;
      module_kind: string;
      config: Record<string, any>;
      inputs: Array<{
        node_id: string;
        name: string;
        type: string;
        position_index: number;
        group_index: number;
      }>;
      outputs: Array<{
        node_id: string;
        name: string;
        type: string;
        position_index: number;
        group_index: number;
      }>;
    }>;
    connections: Array<{
      from_node_id: string;
      to_node_id: string;
    }>;
  };
}

export interface ValidatePipelineResponse {
  valid: boolean;
  error: ValidationError | null;
}
