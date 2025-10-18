// Domain types for Pipelines feature

export type PipelineStatus = 'draft' | 'active' | 'inactive';

// =============================================================================
// Nested Types
// =============================================================================

export interface PipelineVersionSummary {
  version_id: number;
  version_num: number;
  usage_count: number; // ETO runs that used this version
}

// =============================================================================
// List/Summary View
// =============================================================================

export interface PipelineListItem {
  id: number;
  name: string;
  description: string | null;
  status: PipelineStatus;
  current_version: PipelineVersionSummary;
  total_versions: number; // Count of all versions for this pipeline
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

// =============================================================================
// Detail View
// =============================================================================

export interface PipelineDetail extends PipelineListItem {
  // Pipeline state (execution data)
  entry_points: Array<{
    node_id: string;
    name: string;
    type: string;
  }>;
  modules: Array<{
    module_instance_id: string;
    module_id: string;
    config: Record<string, any>;
    inputs: Array<{
      node_id: string;
      name: string;
      type: string;
    }>;
    outputs: Array<{
      node_id: string;
      name: string;
      type: string;
    }>;
  }>;
  connections: Array<{
    connection_id: string;
    source_node_id: string;
    target_node_id: string;
    source_pin_id: string;
    target_pin_id: string;
  }>;
  // Visual state (UI positioning)
  visual_state: {
    positions: Record<string, { x: number; y: number }>;
  };
}

// =============================================================================
// API Response Types
// =============================================================================

export interface PipelinesListResponse {
  items: PipelineListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PipelineDetailResponse {
  pipeline: PipelineDetail;
}

export interface CreatePipelineRequest {
  name: string;
  description?: string;
  entry_points: Array<{
    node_id: string;
    name: string;
    type: string;
  }>;
  modules: Array<{
    module_instance_id: string;
    module_id: string;
    config: Record<string, any>;
    inputs: Array<{
      node_id: string;
      name: string;
      type: string;
    }>;
    outputs: Array<{
      node_id: string;
      name: string;
      type: string;
    }>;
  }>;
  connections: Array<{
    connection_id: string;
    source_node_id: string;
    target_node_id: string;
    source_pin_id: string;
    target_pin_id: string;
  }>;
  visual_state: {
    positions: Record<string, { x: number; y: number }>;
  };
}

export interface UpdatePipelineRequest {
  name?: string;
  description?: string;
  status?: PipelineStatus;
}
