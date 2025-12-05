/**
 * Email Configs API Types
 * Request and response types for API endpoints
 */

import type { FilterRule } from '../types';

// ============================================================================
// Create Request (POST /email-configs)
// ============================================================================

export interface CreateEmailConfigRequest {
  name: string;
  account_id: number;
  folder_name: string;
  description?: string;
  filter_rules?: FilterRule[];
  poll_interval_seconds?: number;
}

// ============================================================================
// Update Request (PUT /email-configs/{id})
// ============================================================================

export interface UpdateEmailConfigRequest {
  name?: string;
  description?: string | null;
  folder_name?: string;
  filter_rules?: FilterRule[];
  poll_interval_seconds?: number;
}

// ============================================================================
// Query Parameters (GET /email-configs)
// ============================================================================

export interface EmailConfigsListQueryParams {
  order_by?: 'name' | 'is_active' | 'last_check_time';
  desc?: boolean;
}

// ============================================================================
// Legacy types (keeping for backwards compatibility during migration)
// ============================================================================

export interface DiscoverFoldersRequest {
  provider_type: string;
  provider_settings: Record<string, any>;
}

export interface ValidateEmailConfigRequest {
  provider_type: string;
  provider_settings: Record<string, any>;
  folder_name: string;
}

export interface ValidateEmailConfigResponse {
  email_address: string;
  folder_name: string;
  message: string;
}
