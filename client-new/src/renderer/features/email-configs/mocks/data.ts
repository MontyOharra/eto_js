/**
 * Email Configurations - Mock Data
 * Test data for all email-configs endpoints
 */

import type {
  EmailConfigListItem,
  EmailConfigDetail,
  EmailAccount,
  EmailFolder,
  FilterRule,
} from '../types';

// ========================================
// Mock Email Accounts (for discovery)
// ========================================

export const mockEmailAccounts: EmailAccount[] = [
  {
    email_address: 'operations@acmelogistics.com',
    display_name: 'ACME Logistics Operations',
  },
  {
    email_address: 'shipping@acmelogistics.com',
    display_name: 'ACME Shipping Department',
  },
  {
    email_address: 'admin@acmelogistics.com',
    display_name: 'ACME Administration',
  },
];

// ========================================
// Mock Email Folders (for discovery)
// ========================================

export const mockEmailFoldersByAccount: Record<string, EmailFolder[]> = {
  'operations@acmelogistics.com': [
    { folder_name: 'Inbox', folder_path: 'Inbox' },
    { folder_name: 'HAWBs', folder_path: 'Inbox/HAWBs' },
    { folder_name: 'Invoices', folder_path: 'Inbox/Invoices' },
    { folder_name: 'Shipment Notices', folder_path: 'Inbox/Shipment Notices' },
    { folder_name: 'Archive', folder_path: 'Archive' },
    { folder_name: 'Sent Items', folder_path: 'Sent Items' },
  ],
  'shipping@acmelogistics.com': [
    { folder_name: 'Inbox', folder_path: 'Inbox' },
    { folder_name: 'Customs Documents', folder_path: 'Inbox/Customs Documents' },
    { folder_name: 'Carriers', folder_path: 'Inbox/Carriers' },
    { folder_name: 'Archive', folder_path: 'Archive' },
  ],
  'admin@acmelogistics.com': [
    { folder_name: 'Inbox', folder_path: 'Inbox' },
    { folder_name: 'Reports', folder_path: 'Inbox/Reports' },
    { folder_name: 'Archive', folder_path: 'Archive' },
  ],
};

// ========================================
// Mock Email Configurations
// ========================================

// Helper to create mock filter rules
function createMockFilterRule(
  field: FilterRule['field'],
  operation: FilterRule['operation'],
  value: string,
  case_sensitive = false
): FilterRule {
  return { field, operation, value, case_sensitive };
}

// Config 1: Active configuration with no errors
export const mockActiveConfig: EmailConfigDetail = {
  id: 1,
  name: 'Operations HAWB Monitor',
  description: 'Monitors the HAWBs folder for air waybill documents',
  email_address: 'operations@acmelogistics.com',
  folder_name: 'HAWBs',
  filter_rules: [
    createMockFilterRule('sender_email', 'contains', '@carrier.com'),
    createMockFilterRule('has_attachments', 'equals', 'true'),
  ],
  poll_interval_seconds: 60,
  max_backlog_hours: 24,
  error_retry_attempts: 3,
  is_active: true,
  activated_at: '2025-01-10T08:00:00Z',
  is_running: true,
  last_check_time: '2025-01-16T14:30:00Z',
  last_error_message: null,
  last_error_at: null,
};

// Config 2: Active configuration with recent error
export const mockActiveConfigWithError: EmailConfigDetail = {
  id: 2,
  name: 'Shipping Customs Monitor',
  description: 'Monitors customs documents from shipping partners',
  email_address: 'shipping@acmelogistics.com',
  folder_name: 'Customs Documents',
  filter_rules: [
    createMockFilterRule('subject', 'contains', 'customs', false),
    createMockFilterRule('attachment_types', 'contains', 'pdf'),
  ],
  poll_interval_seconds: 300,
  max_backlog_hours: 48,
  error_retry_attempts: 5,
  is_active: true,
  activated_at: '2025-01-12T10:15:00Z',
  is_running: false,
  last_check_time: '2025-01-16T14:25:00Z',
  last_error_message: 'Connection timeout: Failed to connect to email server after 3 attempts',
  last_error_at: '2025-01-16T14:25:00Z',
};

// Config 3: Inactive configuration
export const mockInactiveConfig: EmailConfigDetail = {
  id: 3,
  name: 'Legacy Invoice Monitor',
  description: 'Old invoice monitoring configuration - replaced by new system',
  email_address: 'operations@acmelogistics.com',
  folder_name: 'Invoices',
  filter_rules: [
    createMockFilterRule('sender_email', 'ends_with', '@vendor.com'),
  ],
  poll_interval_seconds: 600,
  max_backlog_hours: 12,
  error_retry_attempts: 2,
  is_active: false,
  activated_at: null,
  is_running: false,
  last_check_time: '2025-01-10T16:00:00Z',
  last_error_message: null,
  last_error_at: null,
};

// Config 4: Recently created, never activated
export const mockDraftConfig: EmailConfigDetail = {
  id: 4,
  name: 'Admin Reports Monitor',
  description: null,
  email_address: 'admin@acmelogistics.com',
  folder_name: 'Reports',
  filter_rules: [],
  poll_interval_seconds: 300,
  max_backlog_hours: 24,
  error_retry_attempts: 3,
  is_active: false,
  activated_at: null,
  is_running: false,
  last_check_time: null,
  last_error_message: null,
  last_error_at: null,
};

// All mock configurations
export const allMockEmailConfigs: EmailConfigDetail[] = [
  mockActiveConfig,
  mockActiveConfigWithError,
  mockInactiveConfig,
  mockDraftConfig,
];

// Summary views for list endpoint
export const allMockEmailConfigsSummary: EmailConfigListItem[] = allMockEmailConfigs.map(
  (config) => ({
    id: config.id,
    name: config.name,
    is_active: config.is_active,
    last_check_time: config.last_check_time,
  })
);

// Grouped by status
export const mockEmailConfigsByStatus = {
  active: allMockEmailConfigs.filter((c) => c.is_active),
  inactive: allMockEmailConfigs.filter((c) => !c.is_active),
};
