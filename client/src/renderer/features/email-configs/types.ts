/**
 * Email Configurations - Domain Types
 * Business entities and domain models for email ingestion
 */

// ============================================================================
// Filter System
// ============================================================================

export type FilterRuleField =
  | 'sender_email'
  | 'subject'
  | 'has_attachments'
  | 'received_date';

export type FilterRuleOperation =
  | 'contains'
  | 'equals'
  | 'starts_with'
  | 'ends_with'
  | 'before'
  | 'after'
  | 'is';

export interface FilterRule {
  field: FilterRuleField;
  operation: FilterRuleOperation;
  value: string;
  case_sensitive: boolean;
}

// ============================================================================
// Email Ingestion Configuration Entities
// ============================================================================

/**
 * Ingestion config list item with account info
 * Used in config listings/tables - matches IngestionConfigWithAccountResponse
 */
export interface IngestionConfigListItem {
  id: number;
  name: string;
  description: string | null;
  account_id: number;
  account_name: string;
  account_email: string;
  folder_name: string;
  is_active: boolean;
  last_check_time: string | null;
  last_error_message: string | null;
}

/**
 * Full ingestion config response
 * Matches IngestionConfigResponse from backend
 */
export interface IngestionConfigDetail {
  id: number;
  name: string;
  description: string | null;
  account_id: number;
  folder_name: string;
  filter_rules: FilterRule[];
  poll_interval_seconds: number;
  use_idle: boolean;
  is_active: boolean;
  activated_at: string | null;
  last_check_time: string | null;
  last_processed_uid: number | null;
  last_error_message: string | null;
  last_error_at: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Legacy types (for backwards compatibility during migration)
// ============================================================================

/** @deprecated Use IngestionConfigListItem instead */
export type EmailConfigListItem = IngestionConfigListItem;

/** @deprecated Use IngestionConfigDetail instead */
export type EmailConfigDetail = IngestionConfigDetail;

export interface EmailFolder {
  folder_name: string;
  folder_path: string;
}
