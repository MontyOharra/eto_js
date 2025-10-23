/**
 * Email Configurations - Mock API Hook
 * Implements all 10 email-configs endpoints with realistic behavior
 */

import { useState } from 'react';
import type {
  EmailConfigListItem,
  EmailConfigDetail,
  EmailAccount,
  EmailFolder,
  FilterRule,
} from '../types';
import {
  allMockEmailConfigs,
  allMockEmailConfigsSummary,
  mockEmailAccounts,
  mockEmailFoldersByAccount,
} from '../mocks/data';

// Simulated network delay
const simulateDelay = () =>
  new Promise((resolve) => setTimeout(resolve, Math.random() * 500 + 300));

// In-memory state for CRUD operations
let configsState: EmailConfigDetail[] = [...allMockEmailConfigs];
let nextId = 5; // Start after existing mock IDs

export function useMockEmailConfigsApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ========================================
  // GET /email-configs
  // ========================================
  const getEmailConfigs = async (params?: {
    order_by?: 'name' | 'is_active' | 'last_check_time';
    desc?: boolean;
  }): Promise<EmailConfigListItem[]> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      // Convert to summary view
      let configs = configsState.map((config) => ({
        id: config.id,
        name: config.name,
        is_active: config.is_active,
        last_check_time: config.last_check_time,
      }));

      // Sort
      if (params?.order_by) {
        configs.sort((a, b) => {
          let aVal: any = a[params.order_by!];
          let bVal: any = b[params.order_by!];

          // Handle null values
          if (aVal === null) aVal = '';
          if (bVal === null) bVal = '';

          if (params.desc) {
            return aVal > bVal ? -1 : 1;
          } else {
            return aVal > bVal ? 1 : -1;
          }
        });
      }

      return configs;
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // GET /email-configs/{id}
  // ========================================
  const getEmailConfigDetail = async (id: number): Promise<EmailConfigDetail> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      const config = configsState.find((c) => c.id === id);
      if (!config) {
        throw new Error(`Configuration not found: ${id}`);
      }

      return config;
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // POST /email-configs
  // ========================================
  const createEmailConfig = async (data: {
    name: string;
    description?: string;
    email_address: string;
    folder_name: string;
    filter_rules?: FilterRule[];
    poll_interval_seconds?: number;
    max_backlog_hours?: number;
    error_retry_attempts?: number;
  }): Promise<EmailConfigDetail> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      // Validation
      if (!data.name || data.name.length < 1 || data.name.length > 255) {
        throw new Error('Configuration name must be between 1 and 255 characters');
      }
      if (data.description && data.description.length > 1000) {
        throw new Error('Description must be max 1000 characters');
      }
      if (!data.email_address || !data.email_address.includes('@')) {
        throw new Error('Invalid email address');
      }
      if (!data.folder_name || data.folder_name.length < 1) {
        throw new Error('Folder name is required');
      }
      if (data.poll_interval_seconds !== undefined && data.poll_interval_seconds < 5) {
        throw new Error('Poll interval must be at least 5 seconds');
      }
      if (data.max_backlog_hours !== undefined && data.max_backlog_hours < 1) {
        throw new Error('Max backlog hours must be at least 1');
      }
      if (
        data.error_retry_attempts !== undefined &&
        (data.error_retry_attempts < 1 || data.error_retry_attempts > 10)
      ) {
        throw new Error('Error retry attempts must be between 1 and 10');
      }

      // Create new config
      const newConfig: EmailConfigDetail = {
        id: nextId++,
        name: data.name,
        description: data.description || null,
        email_address: data.email_address,
        folder_name: data.folder_name,
        filter_rules: data.filter_rules || [],
        poll_interval_seconds: data.poll_interval_seconds || 5,
        max_backlog_hours: data.max_backlog_hours || 24,
        error_retry_attempts: data.error_retry_attempts || 3,
        is_active: false,
        activated_at: null,
        is_running: false,
        last_check_time: null,
        last_error_message: null,
        last_error_at: null,
      };

      configsState.push(newConfig);
      return newConfig;
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // PUT /email-configs/{id}
  // ========================================
  const updateEmailConfig = async (
    id: number,
    data: {
      description?: string | null;
      filter_rules?: FilterRule[];
      poll_interval_seconds?: number;
      max_backlog_hours?: number;
      error_retry_attempts?: number;
    }
  ): Promise<EmailConfigDetail> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      const config = configsState.find((c) => c.id === id);
      if (!config) {
        throw new Error(`Configuration not found: ${id}`);
      }

      // Cannot update active configuration
      if (config.is_active) {
        throw new Error('Cannot update active configuration. Deactivate first.');
      }

      // Validation
      if (data.poll_interval_seconds !== undefined && data.poll_interval_seconds < 5) {
        throw new Error('Poll interval must be at least 5 seconds');
      }
      if (data.max_backlog_hours !== undefined && data.max_backlog_hours < 1) {
        throw new Error('Max backlog hours must be at least 1');
      }
      if (
        data.error_retry_attempts !== undefined &&
        (data.error_retry_attempts < 1 || data.error_retry_attempts > 10)
      ) {
        throw new Error('Error retry attempts must be between 1 and 10');
      }

      // Update config
      Object.assign(config, {
        description: data.description !== undefined ? data.description : config.description,
        filter_rules: data.filter_rules !== undefined ? data.filter_rules : config.filter_rules,
        poll_interval_seconds:
          data.poll_interval_seconds !== undefined
            ? data.poll_interval_seconds
            : config.poll_interval_seconds,
        max_backlog_hours:
          data.max_backlog_hours !== undefined
            ? data.max_backlog_hours
            : config.max_backlog_hours,
        error_retry_attempts:
          data.error_retry_attempts !== undefined
            ? data.error_retry_attempts
            : config.error_retry_attempts,
      });

      return config;
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // DELETE /email-configs/{id}
  // ========================================
  const deleteEmailConfig = async (id: number): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      const configIndex = configsState.findIndex((c) => c.id === id);
      if (configIndex === -1) {
        throw new Error(`Configuration not found: ${id}`);
      }

      const config = configsState[configIndex];

      // Cannot delete active configuration
      if (config.is_active) {
        throw new Error('Cannot delete active configuration. Deactivate first.');
      }

      configsState.splice(configIndex, 1);
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // POST /email-configs/{id}/activate
  // ========================================
  const activateEmailConfig = async (id: number): Promise<EmailConfigDetail> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      const config = configsState.find((c) => c.id === id);
      if (!config) {
        throw new Error(`Configuration not found: ${id}`);
      }

      // Update config
      config.is_active = true;
      config.activated_at = new Date().toISOString();
      config.is_running = true;

      return config;
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // POST /email-configs/{id}/deactivate
  // ========================================
  const deactivateEmailConfig = async (id: number): Promise<EmailConfigDetail> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      const config = configsState.find((c) => c.id === id);
      if (!config) {
        throw new Error(`Configuration not found: ${id}`);
      }

      // Update config
      config.is_active = false;
      config.is_running = false;

      return config;
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // GET /email-configs/discovery/accounts
  // ========================================
  const getEmailAccounts = async (): Promise<EmailAccount[]> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();
      return mockEmailAccounts;
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // GET /email-configs/discovery/folders
  // ========================================
  const getEmailFolders = async (email_address: string): Promise<EmailFolder[]> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      if (!email_address) {
        throw new Error('Missing or invalid email_address parameter');
      }

      const folders = mockEmailFoldersByAccount[email_address];
      if (!folders) {
        throw new Error('Email account not found or inaccessible');
      }

      return folders;
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // POST /email-configs/validate
  // ========================================
  const validateEmailConfig = async (data: {
    email_address: string;
    folder_name: string;
  }): Promise<{ email_address: string; folder_name: string; message: string }> => {
    setIsLoading(true);
    setError(null);
    try {
      await simulateDelay();

      // Check if email exists
      const accountExists = mockEmailAccounts.some(
        (acc) => acc.email_address === data.email_address
      );
      if (!accountExists) {
        throw new Error('Cannot connect to email account');
      }

      // Check if folder exists
      const folders = mockEmailFoldersByAccount[data.email_address];
      const folderExists = folders?.some((f) => f.folder_name === data.folder_name);
      if (!folderExists) {
        throw new Error('Folder does not exist or is not accessible');
      }

      return {
        email_address: data.email_address,
        folder_name: data.folder_name,
        message: 'Configuration is valid',
      };
    } finally {
      setIsLoading(false);
    }
  };

  return {
    // Endpoints
    getEmailConfigs,
    getEmailConfigDetail,
    createEmailConfig,
    updateEmailConfig,
    deleteEmailConfig,
    activateEmailConfig,
    deactivateEmailConfig,
    getEmailAccounts,
    getEmailFolders,
    validateEmailConfig,

    // State
    isLoading,
    error,
  };
}
