/**
 * Email Configurations Feature
 * Public API for email config management
 */

// ============================================================================
// Domain Types
// ============================================================================

export type {
  // Filter System
  FilterRuleField,
  FilterRuleOperation,
  FilterRule,

  // Entities
  EmailConfigListItem,
  EmailConfigDetail,
  EmailFolder,

  // Provider Settings
  ImapProviderSettings,
  GraphApiProviderSettings,
  ProviderSettings,
} from './types';

// ============================================================================
// API Types
// ============================================================================

export type {
  CreateEmailConfigRequest,
  UpdateEmailConfigRequest,
  ValidateEmailConfigRequest,
  ValidateEmailConfigResponse,
  DiscoverFoldersRequest,
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
