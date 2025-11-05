/**
 * Email Configurations - Domain Types
 * These types represent the business domain model for email ingestion configurations
 */

// Re-export API types as domain types (they are identical)
export type {
  FilterRuleField,
  FilterRuleOperation,
  FilterRule,
  EmailConfigListItem,
  EmailConfigDetail,
  EmailFolder,
  CreateEmailConfigRequest,
} from './api/types';
