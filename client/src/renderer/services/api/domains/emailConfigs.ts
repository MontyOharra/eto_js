/**
 * Email Configs API Client
 * Matches FastAPI router: /email-configs
 */

import { BaseApiClient } from '../base/apiClient';

// Types matching the FastAPI backend models exactly

export interface EmailFilterRule {
  field: string;
  operation: string;
  value: string;
  case_sensitive: boolean;
}

export interface EmailConfigBase {
  name: string;
  description?: string;
  email_address: string;
  folder_name: string;
  filter_rules: EmailFilterRule[];
  poll_interval_seconds: number;
  max_backlog_hours: number;
  error_retry_attempts: number;
}

export interface EmailConfig extends EmailConfigBase {
  id: number;
  is_active: boolean;
  is_running: boolean;
  emails_processed: number;
  pdfs_found: number;
  last_error_message?: string;
  last_error_at?: string;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
  // Progress tracking fields
  activated_at?: string;
  last_check_time?: string;
  total_emails_processed: number;
  total_pdfs_found: number;
}

export interface EmailConfigCreate extends EmailConfigBase {}

export interface EmailConfigUpdate {
  name?: string;
  description?: string;
  email_address?: string;
  folder_name?: string;
  filter_rules?: EmailFilterRule[];
  poll_interval_seconds?: number;
  max_backlog_hours?: number;
  error_retry_attempts?: number;
}

export interface EmailAccount {
  email_address: string;
  display_name: string;
  account_type: string;
  is_default: boolean;
  provider_specific_id?: string;
}

export interface EmailFolder {
  name: string;
  full_path: string;
  message_count: number;
  unread_count: number;
  folder_type?: string;
  parent_folder?: string;
}

export interface ServiceStatusResponse {
  service: string;
  status: 'up' | 'down';
  message: string;
}

export interface ActivationResponse {
  message: string;
  config: EmailConfig;
}

/**
 * Email Configuration API client
 * Prefix: /email-configs
 */
export class EmailConfigsApiClient extends BaseApiClient {
  /**
   * Create new email configuration
   * POST /email-configs/
   */
  async createConfig(config: EmailConfigCreate): Promise<EmailConfig> {
    return this.post<EmailConfig>('/email-configs/', config);
  }

  /**
   * List all email configurations
   * GET /email-configs/
   */
  async getConfigs(): Promise<EmailConfig[]> {
    return this.get<EmailConfig[]>('/email-configs/');
  }

  /**
   * Get specific email configuration by ID
   * GET /email-configs/{config_id}
   */
  async getConfig(configId: number): Promise<EmailConfig> {
    return this.get<EmailConfig>(`/email-configs/${configId}`);
  }

  /**
   * Update email configuration
   * PUT /email-configs/{config_id}
   */
  async updateConfig(configId: number, update: EmailConfigUpdate): Promise<EmailConfig> {
    return this.put<EmailConfig>(`/email-configs/${configId}`, update);
  }

  /**
   * Activate or deactivate email configuration
   * PATCH /email-configs/{config_id}/activate?activate={true|false}
   */
  async toggleActivation(configId: number, activate: boolean): Promise<ActivationResponse> {
    return this.patch<ActivationResponse>(`/email-configs/${configId}/activate?activate=${activate}`);
  }

  /**
   * Activate email configuration
   * PATCH /email-configs/{config_id}/activate?activate=true
   */
  async activateConfig(configId: number): Promise<ActivationResponse> {
    return this.toggleActivation(configId, true);
  }

  /**
   * Deactivate email configuration
   * PATCH /email-configs/{config_id}/activate?activate=false
   */
  async deactivateConfig(configId: number): Promise<ActivationResponse> {
    return this.toggleActivation(configId, false);
  }

  /**
   * Discover all email accounts available in Outlook
   * GET /email-configs/discovery/accounts
   */
  async discoverAccounts(): Promise<EmailAccount[]> {
    return this.get<EmailAccount[]>('/email-configs/discovery/accounts');
  }

  /**
   * Discover folders for specific email account
   * GET /email-configs/discovery/folders?email_address={email}
   */
  async discoverFolders(emailAddress: string): Promise<EmailFolder[]> {
    return this.get<EmailFolder[]>(`/email-configs/discovery/folders?email_address=${encodeURIComponent(emailAddress)}`);
  }

  /**
   * Get email configs service status
   * GET /email-configs/status
   */
  async getServiceStatus(): Promise<ServiceStatusResponse> {
    return this.get<ServiceStatusResponse>('/email-configs/status');
  }
}