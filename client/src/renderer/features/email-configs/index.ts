/**
 * Email Configurations Feature
 * Public API for email ingestion config management
 */

// ============================================================================
// Domain Types
// ============================================================================

export type {
  // Filter System
  FilterRuleField,
  FilterRuleOperation,
  FilterRule,

  // New Entities
  IngestionConfigListItem,
  IngestionConfigDetail,

  // Legacy aliases (deprecated)
  EmailConfigListItem,
  EmailConfigDetail,
  EmailFolder,
} from './types';

// ============================================================================
// API Types
// ============================================================================

export type {
  CreateEmailConfigRequest,
  UpdateEmailConfigRequest,
  EmailConfigsListQueryParams,
} from './api/types';

// ============================================================================
// API Hooks
// ============================================================================

export { useEmailConfigsApi } from './api/hooks';

// ============================================================================
// Components
// ============================================================================

export {
  EmailConfigCard,
  EmailConfigWizard,
  EditConfigModal,
} from './components';
