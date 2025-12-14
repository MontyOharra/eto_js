/**
 * System Settings API Types
 * Type definitions for system settings API requests and responses
 */

// ========== Email Settings ==========

export interface EmailSettingsResponse {
  default_sender_account_id: number | null;
}

export interface UpdateEmailSettingsRequest {
  default_sender_account_id: number | null;
}
