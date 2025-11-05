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
  EmailFolder,
  CreateEmailConfigRequest,
} from './types';

// Components
export {
  EmailConfigCard,
  EmailConfigWizard,
  EditConfigModal,
} from './components';