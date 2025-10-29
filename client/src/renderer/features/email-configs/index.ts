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

// Components
export {
  EmailConfigCard,
  StatusBadge,
  EmailConfigWizard,
  EditConfigModal,
} from './components';
export type { WizardData } from './components';