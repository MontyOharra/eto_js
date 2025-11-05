/**
 * Email Configs API Types
 * Request and response types for API endpoints
 */

import type { FilterRule } from '../types';

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
// Query Parameters (GET /email-configs)
// ============================================================================

export interface EmailConfigsListQueryParams {
  order_by?: 'name' | 'is_active' | 'last_check_time';
  desc?: boolean;
}
