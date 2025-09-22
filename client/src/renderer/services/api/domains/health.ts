/**
 * Health API Client
 * Matches FastAPI health router: /health
 */

import { BaseApiClient } from '../base/apiClient';

// Types matching the FastAPI backend health responses
export interface BasicHealthResponse {
  status: string;
  timestamp: string;
  service: string;
}

export interface ServiceStatusDetail {
  status: string;
  message: string;
}

export interface DatabaseStatus {
  status: string;
  message: string;
}

export interface StorageStatus {
  status: string;
  message: string;
  details?: any;
}

export interface DetailedServiceStatus {
  overall_status: string;
  timestamp: string;
  services: {
    pdf_processing?: ServiceStatusDetail;
    email_ingestion?: ServiceStatusDetail;
    pdf_templates?: ServiceStatusDetail;
    container?: ServiceStatusDetail;
  };
  database: DatabaseStatus;
  storage: StorageStatus;
}

export interface ReadinessResponse {
  ready: boolean;
  message: string;
  timestamp: string;
}

/**
 * Health API client for system health monitoring
 * Endpoints: /health, /health/status, /health/ready
 */
export class HealthApiClient extends BaseApiClient {
  /**
   * Basic health check
   * GET /health/
   */
  async getHealth(): Promise<BasicHealthResponse> {
    return this.get<BasicHealthResponse>('/health/');
  }

  /**
   * Detailed service status check
   * GET /health/status
   */
  async getServiceStatus(): Promise<DetailedServiceStatus> {
    return this.get<DetailedServiceStatus>('/health/status');
  }

  /**
   * Readiness check for critical services
   * GET /health/ready
   */
  async getReadiness(): Promise<ReadinessResponse> {
    return this.get<ReadinessResponse>('/health/ready');
  }
}