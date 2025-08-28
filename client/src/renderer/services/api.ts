/**
 * API Client for ETO Backend Service
 * Handles all HTTP communication with the Flask backend
 */

// Backend API Response Types
export interface ApiEtoRun {
  id: number;
  email_id: number;
  pdf_file_id: number;
  status: "success" | "failure" | "unrecognized" | "processing" | "error";
  matched_template_id?: number;
  error_type?: string;
  error_message?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  pdf_file: {
    original_filename: string;
    sha256_hash: string;
    file_size: number;
  };
  email: {
    subject: string;
    sender_email: string;
    received_date: string;
  };
}

export interface ApiEtoRunsResponse {
  eto_runs: ApiEtoRun[];
  total: number;
  status_filter?: string;
}

export interface ApiSystemStats {
  database: {
    emails_count: number;
    pdf_files_count: number;
    eto_runs_count: number;
    templates_count: number;
    cursors_count: number;
  };
  storage: {
    total_files: number;
    total_size_mb: number;
    avg_file_size_kb: number;
  };
  processing: {
    success_rate: number;
    avg_processing_time_ms: number;
    total_processed: number;
  };
}

export interface ApiEmailStatus {
  monitoring: boolean;
  current_email?: string;
  current_folder?: string;
  connected: boolean;
  last_check?: string;
  error?: string;
}

export interface ApiTemplate {
  id: number;
  name: string;
  customer_name?: string;
  description?: string;
  status: "active" | "archived" | "draft";
  is_complete: boolean;
  coverage_threshold: number;
  usage_count: number;
  last_used_at?: string;
  success_rate?: number;
  version: number;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  extraction_rules_count: number;
  signature_object_count: number;
}

export interface ApiTemplatesResponse {
  templates: ApiTemplate[];
  total: number;
  status_filter?: string;
}

export interface ApiError {
  error: string;
  details?: any;
}

// API Configuration
const API_BASE_URL = 'http://localhost:8080';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Generic fetch wrapper with error handling
   */
  private async fetchApi<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(`HTTP ${response.status}: ${response.statusText}`, errorData);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      // Network or parsing errors
      throw new ApiError(`Network error: ${error.message}`, error);
    }
  }

  /**
   * Health Check
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.fetchApi('/health');
  }

  /**
   * Get ETO Runs
   */
  async getEtoRuns(params?: {
    status?: string;
    limit?: number;
  }): Promise<ApiEtoRunsResponse> {
    const searchParams = new URLSearchParams();
    
    if (params?.status) {
      searchParams.append('status', params.status);
    }
    if (params?.limit) {
      searchParams.append('limit', params.limit.toString());
    }

    const endpoint = `/api/eto-runs${searchParams.toString() ? `?${searchParams}` : ''}`;
    return this.fetchApi<ApiEtoRunsResponse>(endpoint);
  }

  /**
   * Get System Statistics
   */
  async getSystemStats(): Promise<ApiSystemStats> {
    return this.fetchApi('/api/system/stats');
  }

  /**
   * Get Email Status
   */
  async getEmailStatus(): Promise<ApiEmailStatus> {
    return this.fetchApi('/api/email/status');
  }

  /**
   * Start Email Monitoring
   */
  async startEmailMonitoring(params?: {
    email_address?: string;
    folder_name?: string;
  }): Promise<{ success: boolean; message: string }> {
    return this.fetchApi('/api/email/start', {
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  }

  /**
   * Stop Email Monitoring
   */
  async stopEmailMonitoring(): Promise<{ success: boolean; message: string }> {
    return this.fetchApi('/api/email/stop', {
      method: 'POST',
    });
  }

  /**
   * Get Templates
   */
  async getTemplates(params?: {
    status?: string;
    limit?: number;
  }): Promise<ApiTemplatesResponse> {
    const searchParams = new URLSearchParams();
    
    if (params?.status) {
      searchParams.append('status', params.status);
    }
    if (params?.limit) {
      searchParams.append('limit', params.limit.toString());
    }

    const endpoint = `/api/templates${searchParams.toString() ? `?${searchParams}` : ''}`;
    return this.fetchApi<ApiTemplatesResponse>(endpoint);
  }

  /**
   * Get PDF File (binary data)
   */
  getPdfFileUrl(pdfId: number): string {
    return `${this.baseUrl}/api/pdf/${pdfId}`;
  }

  /**
   * Get PDF Objects
   */
  async getPdfObjects(pdfId: number): Promise<{
    pdf_id: number;
    filename: string;
    page_count: number;
    object_count: number;
    objects: any[];
  }> {
    return this.fetchApi(`/api/pdf/${pdfId}/objects`);
  }

  /**
   * Get ETO Run PDF Data (complete PDF data including objects)
   */
  async getEtoRunPdfData(runId: string | number): Promise<{
    eto_run_id: number;
    pdf_id: number;
    filename: string;
    page_count: number;
    object_count: number;
    file_size: number;
    raw_extracted_data?: string;
    email: {
      subject: string;
      sender_email: string;
      received_date: string;
    };
    status: string;
    error_message?: string;
  }> {
    return this.fetchApi(`/api/eto-run/${runId}/pdf-data`);
  }

  /**
   * Create Template
   */
  async createTemplate(templateData: {
    name: string;
    description?: string;
    source_pdf_id: number;
    source_eto_run_id: number;
    filename: string;
    selected_objects: any[];
  }): Promise<{
    template_id: number;
    message: string;
  }> {
    return this.fetchApi('/api/templates', {
      method: 'POST',
      body: JSON.stringify(templateData),
    });
  }

  /**
   * Test Template Matching (for debugging)
   */
  async testTemplateMatch(pdfId: number, templateId: number): Promise<{
    test_results: {
      pdf_info: any;
      template_info: any;
      signature_analysis: any;
      direct_match_test: any;
      full_matching_result: any;
      would_match: boolean;
    };
  }> {
    return this.fetchApi('/api/test/template-match', {
      method: 'POST',
      body: JSON.stringify({
        pdf_id: pdfId,
        template_id: templateId
      }),
    });
  }

  /**
   * Trigger Reprocessing of Unrecognized ETO Runs
   */
  async triggerReprocessing(): Promise<{
    success: boolean;
    result: {
      reprocessed: number;
      message: string;
      error?: string;
    };
  }> {
    return this.fetchApi('/api/templates/reprocess', {
      method: 'POST',
    });
  }

  /**
   * Generic GET request (for flexibility)
   */
  async get<T = any>(endpoint: string): Promise<{ data: T }> {
    const data = await this.fetchApi<T>(endpoint);
    return { data };
  }
}

// Custom error class for API errors
export class ApiError extends Error {
  public details?: any;

  constructor(message: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.details = details;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types
export type { ApiEtoRun, ApiEtoRunsResponse, ApiSystemStats, ApiEmailStatus, ApiTemplate, ApiTemplatesResponse };