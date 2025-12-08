/**
 * Modules Feature
 * Public API for module catalog access
 */

// ============================================================================
// Domain Types
// ============================================================================

export type {
  // I/O Shape System
  NodeTypeRule,
  NodeGroup,
  IOSideShape,
  IOShape,
  ModuleMeta,

  // Module Template
  ModuleTemplate,

  // Output Channel Types
  OutputChannelType,
} from './types';

// ============================================================================
// API Types
// ============================================================================

export type {
  Module,
  ModulesQueryParams,
} from './api/types';

// ============================================================================
// API Hooks
// ============================================================================

export { useModules, useModule, useOutputChannels } from './api/hooks';

// ============================================================================
// Components
// ============================================================================

export { ModuleSelectorPane } from './components/ModuleSelectorPane';
