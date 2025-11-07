/**
 * Pipelines Feature
 * Pipeline creation, execution, and management
 */

// ============================================================================
// Domain Types
// ============================================================================

export type {
  ModuleInstance,
  NodePin,
  // Pipeline domain types
  NodeConnection,
  EntryPoint,
  PipelineState,
  VisualState,
  PipelineData,
} from './types';

// ============================================================================
// API Types & Hooks
// ============================================================================

export type {
  // List endpoint
  PipelineSummary,
  PipelinesListResponse,
  // Detail endpoint
  PipelineDetail,
  // Create endpoint
  CreatePipelineRequest,
  CreatePipelineResponse,
  // Validation endpoint
  ValidationError,
  ValidatePipelineRequest,
  ValidatePipelineResponse,
  // Execution endpoint
  ExecutePipelineRequest,
  ExecutePipelineResponse,
  ExecutionStepResult,
  // Query params
  PipelinesQueryParams,
} from './api/types';

export { usePipelinesApi } from './api/hooks';

// ============================================================================
// Components
// ============================================================================

export { PipelineGraph } from './components/PipelineGraph/PipelineGraph';
export type { PipelineGraphRef } from './components/PipelineGraph/PipelineGraph';

// ============================================================================
// Hooks
// ============================================================================

export { usePipelineValidation } from './hooks/usePipelineValidation';
