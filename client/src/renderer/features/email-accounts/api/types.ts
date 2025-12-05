/**
 * Email Accounts API Types
 * Type definitions matching the backend API schemas
 */

// ========== Provider Settings ==========

export interface ImapProviderSettings {
  host: string;
  port: number;
  use_ssl: boolean;
}

export type ProviderSettings = ImapProviderSettings;

// ========== Credentials ==========

export interface PasswordCredentials {
  type: 'password';
  password: string;
}

export interface OAuthCredentials {
  type: 'oauth';
  access_token: string;
  refresh_token?: string;
  token_expiry?: string;
}

export type Credentials = PasswordCredentials | OAuthCredentials;

// ========== Validation ==========

export interface ValidateConnectionRequest {
  provider_type: string;
  email_address: string;
  provider_settings: ImapProviderSettings;
  credentials: PasswordCredentials;
}

export interface ValidationResultResponse {
  success: boolean;
  message: string;
  capabilities: string[];
  folder_count?: number;
}

// ========== Account CRUD ==========

export interface CreateEmailAccountRequest {
  name: string;
  description?: string;
  provider_type: string;
  email_address: string;
  provider_settings: ImapProviderSettings;
  credentials: PasswordCredentials;
  capabilities: string[];
}

export interface UpdateEmailAccountRequest {
  name?: string;
  description?: string;
  provider_settings?: ImapProviderSettings;
  credentials?: PasswordCredentials;
  is_validated?: boolean;
  capabilities?: string[];
  clear_errors?: boolean;
}

// ========== Response Types ==========

export interface EmailAccountSummary {
  id: number;
  name: string;
  email_address: string;
  provider_type: string;
  is_validated: boolean;
  capabilities: string[];
}

export interface EmailAccountResponse {
  id: number;
  name: string;
  description?: string;
  provider_type: string;
  email_address: string;
  provider_settings: ImapProviderSettings;
  is_validated: boolean;
  validated_at?: string;
  capabilities: string[];
  last_error_message?: string;
  last_error_at?: string;
  created_at: string;
  updated_at: string;
}

export interface EmailAccountListResponse {
  accounts: EmailAccountSummary[];
  total: number;
}

export interface FolderListResponse {
  account_id: number;
  folders: string[];
}

// ========== Query Params ==========

export interface EmailAccountsListQueryParams {
  order_by?: string;
  desc?: boolean;
  validated_only?: boolean;
}
