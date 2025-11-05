/**
 * Email Configs API Types (s)
 * Request and response types matching the backend API
 */

// ============================================================================
// Filter Rule Types
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
// List Response (GET /email-configs)
// ============================================================================

export interface EmailConfigListItem {
  id: number;
  name: string;
  is_active: boolean;
  last_check_time: string | null; // ISO 8601
}

// ============================================================================
// Detail Response (GET /email-configs/{id})
// ============================================================================

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

// ============================================================================
// Provider Settings Types
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

// ============================================================================
// Create Request (POST /email-configs)
// ============================================================================

export interface CreateEmailConfigRequest {
  provider_type: string; // "imap", "graph_api", etc.
  provider_settings: Record<string, any>; // Provider-specific settings
  name: string; // required, 1-255 chars
  description?: string; // optional, max 1000 chars
  folder_name: string; // required, min 1 char
  filter_rules?: FilterRule[]; // optional, default: []
  poll_interval_seconds?: number; // optional, min: 5, default: 5
}

// ============================================================================
// Update Request (PUT /email-configs/{id})
// ============================================================================

export interface UpdateEmailConfigRequest {
  description?: string | null;
  filter_rules?: FilterRule[];
  poll_interval_seconds?: number; // min: 5
}

// ============================================================================
// Discovery: Folders (POST /email-configs/discovery/folders)
// ============================================================================

export interface DiscoverFoldersRequest {
  provider_type: string;
  provider_settings: Record<string, any>;
}

export interface EmailFolder {
  folder_name: string;
  folder_path: string; // full path
}

// ============================================================================
// Validation Request/Response (POST /email-configs/validate)
// ============================================================================

export interface ValidateEmailConfigRequest {
  provider_type: string;
  provider_settings: Record<string, any>;
  folder_name: string;
}

export interface ValidateEmailConfigResponse {
  email_address: string;
  folder_name: string;
  message: string; // "Configuration is valid"
}

// ============================================================================
// Query Parameters
// ============================================================================

export interface EmailConfigsListQueryParams {
  order_by?: 'name' | 'is_active' | 'last_check_time';
  desc?: boolean;
}
