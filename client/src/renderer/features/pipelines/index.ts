/**
 * Pipelines Feature
 * Pipeline creation, execution, and management
 */

// Types (re-exports module types + adds pipeline-specific types)
export type {
  // Module types (re-exported for convenience)
  NodeTypeRule,
  NodeGroup,
  IOSideShape,
  IOShape,
  ModuleTemplate,
  ModuleInstance,
  NodePin,
  // Pipeline-specific types
  NodeConnection,
  EntryPoint,
  BackendEntryPoint,
  PipelineState,
  VisualState,
} from './types';

// Components
export { PipelineGraph } from './components/PipelineGraph';
export type { PipelineGraphRef } from './components/PipelineGraph';

// Hooks
export { usePipelinesApi } from './hooks/usePipelinesApi';
export { usePipelineValidation } from './hooks/usePipelineValidation';
