/**
 * Email Configs API Types (DTOs)
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

export interface FilterRuleDTO {
  field: FilterRuleField;
  operation: FilterRuleOperation;
  value: string;
  case_sensitive: boolean;
}

// ============================================================================
// List Response (GET /email-configs)
// ============================================================================

export interface EmailConfigSummaryDTO {
  id: number;
  name: string;
  is_active: boolean;
  last_check_time: string | null; // ISO 8601
}

// ============================================================================
// Detail Response (GET /email-configs/{id})
// ============================================================================

export interface EmailConfigDetailDTO {
  id: number;
  name: string;
  description: string | null;
  email_address: string;
  folder_name: string;
  filter_rules: FilterRuleDTO[];
  poll_interval_seconds: number;
  is_active: boolean;
  activated_at: string | null; // ISO 8601
  last_check_time: string | null; // ISO 8601
  last_error_message: string | null;
  last_error_at: string | null; // ISO 8601
}

// ============================================================================
// Create Request (POST /email-configs)
// ============================================================================

export interface CreateEmailConfigRequestDTO {
  name: string; // required, 1-255 chars
  description?: string; // optional, max 1000 chars
  email_address: string; // required, valid email
  folder_name: string; // required, min 1 char
  filter_rules?: FilterRuleDTO[]; // optional, default: []
  poll_interval_seconds?: number; // optional, min: 5, default: 5
}

// ============================================================================
// Update Request (PUT /email-configs/{id})
// ============================================================================

export interface UpdateEmailConfigRequestDTO {
  description?: string | null;
  filter_rules?: FilterRuleDTO[];
  poll_interval_seconds?: number; // min: 5
}

// ============================================================================
// Discovery: Email Accounts (GET /email-configs/discovery/accounts)
// ============================================================================

export interface EmailAccountDTO {
  email_address: string;
  display_name: string | null;
}

// ============================================================================
// Discovery: Folders (GET /email-configs/discovery/folders)
// ============================================================================

export interface EmailFolderDTO {
  folder_name: string;
  folder_path: string; // full path
}

// ============================================================================
// Validation Request/Response (POST /email-configs/validate)
// ============================================================================

export interface ValidateEmailConfigRequestDTO {
  email_address: string;
  folder_name: string;
}

export interface ValidateEmailConfigResponseDTO {
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

export interface EmailFoldersQueryParams {
  email_address: string; // required
}
