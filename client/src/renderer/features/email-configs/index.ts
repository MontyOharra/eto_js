/**
 * Email Configurations Feature
 * Public exports for email ingestion configurations
 */

// Types
export type {
  FilterRuleField,
  FilterRuleOperation,
  FilterRule,
  EmailConfigListItem,
  EmailConfigDetail,
  EmailAccount,
  EmailFolder,
} from './types';

// API Hook
export { useMockEmailConfigsApi } from './hooks/useMockEmailConfigsApi';

// Components
export {
  EmailConfigCard,
  StatusBadge,
  EmailConfigWizard,
  EditConfigModal,
} from './components';
export type { WizardData } from './components';

// Mock Data (for testing/reference)
export {
  mockEmailAccounts,
  mockEmailFoldersByAccount,
  allMockEmailConfigs,
  allMockEmailConfigsSummary,
} from './mocks/data';
