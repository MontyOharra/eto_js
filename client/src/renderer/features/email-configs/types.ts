/**
 * Email Configurations - Domain Types
 * These types represent the business domain model for email ingestion configurations
 */

// Re-export API types as domain types (they are identical)
export type {
  FilterRuleField,
  FilterRuleOperation,
  FilterRuleDTO as FilterRule,
  EmailConfigSummaryDTO as EmailConfigListItem,
  EmailConfigDetailDTO as EmailConfigDetail,
  EmailAccountDTO as EmailAccount,
  EmailFolderDTO as EmailFolder,
} from './api/types';
