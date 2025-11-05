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
  | 'attachment_types';

export type FilterRuleOperation =
  | 'contains'
  | 'equals'
  | 'starts_with'
  | 'ends_with';

export interface FilterRule {
  field: FilterRuleField;
  operation: FilterRuleOperation;
  value: string;
  case_sensitive: boolean;
}

// ============================================================================
// Email Configuration Entities
// ============================================================================

/**
 * Email configuration list item
 * Used in config listings/tables
 */
export interface EmailConfigListItem {
  id: number;
  name: string;
  is_active: boolean;
  last_check_time: string | null; // ISO 8601
}

/**
 * Detailed email configuration
 * Full configuration with all fields
 */
export interface EmailConfigDetail {
  id: number;
  name: string;
  description: string | null;
  email_address: string;
  folder_name: string;
  filter_rules: FilterRule[];
  poll_interval_seconds: number;
  is_active: boolean;
  activated_at: string | null; // ISO 8601
  last_check_time: string | null; // ISO 8601
  last_error_message: string | null;
  last_error_at: string | null; // ISO 8601
}

/**
 * Email folder entity
 * Represents a folder in an email account
 */
export interface EmailFolder {
  folder_name: string;
  folder_path: string; // full path
}

// ============================================================================
// Provider Settings
// ============================================================================

export interface ImapProviderSettings {
  host: string;
  port: number;
  email_address: string;
  password: string;
  use_ssl: boolean;
}

export interface GraphApiProviderSettings {
  tenant_id: string;
  client_id: string;
  client_secret: string;
  email_address: string;
}

export type ProviderSettings = ImapProviderSettings | GraphApiProviderSettings;
