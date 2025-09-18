/**
 * API Client for ETO Backend Service
 * Handles all HTTP communication with the Flask backend
 */

// Backend API Response Types
export interface ApiEtoRun {
  id: number;
  email_id: number;
  pdf_file_id: number;
  status: "not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped";
  processing_step?: "template_matching" | "extracting_data" | "transforming_data";

  // Basic metadata
  pdf_filename: string;
  email_subject: string;
  sender_email: string;
  file_size: number;

  // Processing info
  matched_template_id?: number;
  template_name?: string;
  processing_duration_ms?: number;
  error_message?: string;

  // Timestamps
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ApiEtoRunsResponse {
  success: boolean;
  data: ApiEtoRun[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
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

// Email Ingestion Types
export interface EmailIngestionConfig {
  id: number;
  name: string;
  description?: string;
  connection: {
    email_address: string;
    folder_name: string;
  };
  filter_rules?: Array<{
    field: string;
    operation: string;
    value: string;
    case_sensitive: boolean;
  }>;
  monitoring: {
    poll_interval_seconds: number;
    max_backlog_hours: number;
    error_retry_attempts: number;
  };
  is_active: boolean;
  is_running: boolean;
  emails_processed: number;
  pdfs_found: number;
  last_error_message?: string;
  last_error_at?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
}

export interface EmailIngestionConfigSummary {
  id: number;
  name: string;
  folder_name: string;
  is_active: boolean;
  is_running: boolean;
  emails_processed: number;
  pdfs_found: number;
  last_used_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ProcessedEmail {
  id: number;
  message_id: string;
  subject: string;
  sender_email: string;
  sender_name?: string;
  received_date: string;
  folder_name: string;
  has_attachments: boolean;
  attachment_count: number;
  created_at: string;
}

export interface EmailIngestionStatus {
  is_running: boolean;
  current_config?: {
    id: number;
    name: string;
    email_address: string;
    folder_name: string;
  };
  connection_status: {
    is_connected: boolean;
    last_error?: string;
  };
  stats: {
    emails_processed: number;
    pdfs_found: number;
    processing_errors: number;
    last_processed_at?: string;
    uptime_seconds: number;
    reconnections: number;
  };
}

// API Configuration - Updated for unified ETO server
const API_BASE_URL = 'http://localhost:8080/api';

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
    email_id?: number;
    template_id?: number;
    has_errors?: boolean;
    date_from?: string;
    date_to?: string;
    page?: number;
    limit?: number;
    order_by?: string;
    desc?: boolean;
  }): Promise<ApiEtoRunsResponse> {
    const searchParams = new URLSearchParams();

    if (params?.status) {
      searchParams.append('status', params.status);
    }
    if (params?.email_id) {
      searchParams.append('email_id', params.email_id.toString());
    }
    if (params?.template_id) {
      searchParams.append('template_id', params.template_id.toString());
    }
    if (params?.has_errors !== undefined) {
      searchParams.append('has_errors', params.has_errors.toString());
    }
    if (params?.date_from) {
      searchParams.append('date_from', params.date_from);
    }
    if (params?.date_to) {
      searchParams.append('date_to', params.date_to);
    }
    if (params?.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params?.limit) {
      searchParams.append('limit', params.limit.toString());
    }
    if (params?.order_by) {
      searchParams.append('order_by', params.order_by);
    }
    if (params?.desc !== undefined) {
      searchParams.append('desc', params.desc.toString());
    }

    const endpoint = `/api/eto-runs${searchParams.toString() ? `?${searchParams}` : ''}`;
    return this.fetchApi<ApiEtoRunsResponse>(endpoint);
  }

  /**
   * Get ETO Run Details
   */
  async getEtoRunDetails(runId: string | number): Promise<{
    success: boolean;
    data: ApiEtoRun & {
      error_details?: any;
      step_execution_log?: any;
      template_name?: string;
      template_version?: number;
      template_match_coverage?: number;
      failed_step_id?: number;
      order_id?: number;
    };
  }> {
    return this.fetchApi(`/api/eto-runs/${runId}`);
  }

  /**
   * Skip ETO Run
   */
  async skipEtoRun(runId: string | number, params: {
    reason: string;
    permanent?: boolean;
  }): Promise<{
    success: boolean;
    run_id: number;
    status: string;
    reason: string;
    message: string;
  }> {
    return this.fetchApi(`/api/eto-runs/${runId}/skip`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  /**
   * Delete ETO Run
   */
  async deleteEtoRun(runId: string | number): Promise<{
    success: boolean;
    run_id: number;
    message: string;
  }> {
    return this.fetchApi(`/api/eto-runs/${runId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Reprocess ETO Run
   */
  async reprocessEtoRun(runId: string | number, params?: {
    force?: boolean;
    template_id?: number;
    reset_template?: boolean;
    reason?: string;
  }): Promise<{
    success: boolean;
    run_id: number;
    old_status: string;
    new_status: string;
    message: string;
  }> {
    return this.fetchApi(`/api/eto-runs/${runId}/reprocess`, {
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  }

  /**
   * Get ETO Processing Statistics
   */
  async getEtoStatistics(): Promise<{
    success: boolean;
    data: {
      total_runs: number;
      successful_runs: number;
      failed_runs: number;
      skipped_runs: number;
      processing_runs: number;
      needs_template_runs: number;
      success_rate: number;
      avg_processing_time_ms?: number;
      median_processing_time_ms?: number;
      last_24h_runs: number;
      last_7d_runs: number;
      last_30d_runs: number;
      most_common_errors: any[];
      template_coverage: number;
      last_successful_run?: string;
      last_failed_run?: string;
      last_processed_run?: string;
    };
  }> {
    return this.fetchApi('/api/eto-runs/statistics');
  }

  /**
   * Get System Statistics
   */
  async getSystemStats(): Promise<ApiSystemStats> {
    return this.fetchApi('/api/health/metrics');
  }

  /**
   * Get Email Status
   */
  async getEmailStatus(): Promise<ApiEmailStatus> {
    return this.fetchApi('/api/emails');
  }

  /**
   * Start Email Monitoring
   */
  async startEmailMonitoring(params?: {
    email_address?: string;
    folder_name?: string;
  }): Promise<{ success: boolean; message: string }> {
    return this.fetchApi('/api/emails/process', {
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  }

  /**
   * Stop Email Monitoring
   */
  async stopEmailMonitoring(): Promise<{ success: boolean; message: string }> {
    return this.fetchApi('/api/emails/process', {
      method: 'DELETE',
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
    return `${this.baseUrl}/api/pdfs/${pdfId}`;
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
    return this.fetchApi(`/api/pdfs/${pdfId}/objects`);
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
    pdf_objects: any[];  // PDF objects from pdf_files table
    status: "not_started" | "processing" | "success" | "failure" | "needs_template";
    processing_step?: "template_matching" | "extracting_data" | "transforming_data";
    matched_template_id?: number;
    extracted_data?: any;  // Structured extracted field data
    transformation_audit?: any;  // Transformation audit trail
    target_data?: any;  // Final transformed data
    email: {
      subject: string;
      sender_email: string;
      received_date: string;
    };
    timestamps: {
      created_at?: string;
      started_at?: string;
      completed_at?: string;
    };
    error_info: {
      error_type?: string;
      error_message?: string;
    };
  }> {
    return this.fetchApi(`/api/processing/runs/${runId}`);
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
   * Trigger Reprocessing of Failed ETO Runs
   */
  async triggerReprocessing(): Promise<{
    success: boolean;
    result: {
      reprocessed: number;
      message: string;
      needs_template_count: number;
      failure_count: number;
      error?: string;
    };
  }> {
    return this.fetchApi('/api/templates/reprocess', {
      method: 'POST',
    });
  }

  /**
   * Get extraction results for a successful ETO run
   */
  async getExtractionResults(runId: number): Promise<{
    id: number;
    status: string;
    matched_template_id: number;
    template_name: string;
    pdf_id: number;
    filename: string;
    page_count: number;
    extracted_data: Record<string, any>;
    extraction_fields: Array<{
      id: string;
      label: string;
      description: string;
      boundingBox: [number, number, number, number];
      page: number;
      extracted_value: any;
    }>;
    email: {
      subject: string;
      sender_email: string;
      received_date: string;
    };
  }> {
    const response = await fetch(`${this.baseUrl}/api/eto-runs/${runId}/extraction-results`);
    if (!response.ok) {
      throw new Error(`Failed to fetch extraction results: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get detailed processing information for an ETO run
   */
  async getEtoRunProcessingDetails(runId: string | number): Promise<{
    run_id: number;
    status: "not_started" | "processing" | "success" | "failure" | "needs_template";
    processing_step?: "template_matching" | "extracting_data" | "transforming_data";
    template_info?: {
      id: number;
      name: string;
      customer_name?: string;
      description?: string;
    };
    extraction_info: {
      status?: string;
      fields_extracted: number;
      field_names: string[];
      extracted_fields: Record<string, any>;
    };
    transformation_info: Record<string, any>;
    target_data: Record<string, any>;
    processing_times: {
      started_at?: string;
      completed_at?: string;
      duration_seconds?: number;
    };
  }> {
    return this.fetchApi(`/api/eto-runs/${runId}/processing-details`);
  }

  /**
   * Reprocess a single ETO run
   */
  async reprocessSingleEtoRun(runId: string | number): Promise<{
    success: boolean;
    message: string;
    run_id: number;
    old_status: string;
    new_status: string;
  }> {
    return this.fetchApi(`/api/eto-runs/${runId}/reprocess`, {
      method: 'POST',
    });
  }

  /**
   * Get detailed template data for viewing
   */
  async getTemplateViewData(templateId: number): Promise<{
    success: boolean;
    result: {
      id: number;
      name: string;
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
      sample_pdf_id: number;
      sample_pdf_filename: string;
      sample_pdf_page_count: number;
      pdf_objects: any[];
      signature_objects: any[];
      extraction_fields: Array<{
        id: string;
        boundingBox: [number, number, number, number];
        page: number;
        label: string;
        description: string;
        required: boolean;
        validationRegex?: string;
      }>;
    };
    error?: string;
  }> {
    return this.fetchApi(`/api/templates/${templateId}/view`);
  }

  /**
   * Analyze transformation pipeline to generate execution steps
   */
  async analyzePipeline(pipelineData: {
    modules: Array<{
      id: string;
      template: any;
      position: { x: number; y: number };
      config: Record<string, any>;
      nodes: {
        inputs: Array<{
          id: string;
          name: string;
          type: string;
          description: string;
          required: boolean;
        }>;
        outputs: Array<{
          id: string;
          name: string;
          type: string;
          description: string;
          required: boolean;
        }>;
      };
    }>;
    connections: Array<{
      id: string;
      fromModuleId: string;
      fromOutputIndex: number;
      toModuleId: string;
      toInputIndex: number;
    }>;
  }): Promise<{
    success: boolean;
    execution_steps: Array<{
      step: number;
      module_id: string;
      module_name: string;
      operation: string;
      inputs: string[];
      outputs: string[];
      dependencies: string[];
    }>;
    pipeline_info: {
      total_modules: number;
      input_definers: number;
      output_definers: number;
      processing_modules: number;
    };
    error?: string;
  }> {
    return this.fetchApi('/api/pipelines/analyze', {
      method: 'POST',
      body: JSON.stringify(pipelineData),
    });
  }

  /**
   * Get base modules from unified server
   */
  async getBaseModules(): Promise<{
    success: boolean;
    modules: Array<{
      id: string;
      name: string;
      description: string;
      category: string;
      color: string;
      version: string;
      inputs: Array<{
        name: string;
        type: string;
        description: string;
        required: boolean;
      }>;
      outputs: Array<{
        name: string;
        type: string;
        description: string;
        required: boolean;
      }>;
      config: Array<{
        name: string;
        type: string;
        description: string;
        required: boolean;
        defaultValue?: any;
      }>;
      maxInputs?: number;
      maxOutputs?: number;
      dynamicInputs?: any;
      dynamicOutputs?: any;
    }>;
    message?: string;
  }> {
    return this.fetchApi('/api/modules');
  }

  /**
   * Generic GET request (for flexibility)
   */
  async get<T = any>(endpoint: string): Promise<{ data: T }> {
    const data = await this.fetchApi<T>(endpoint);
    return { data };
  }

  // === Email Ingestion API Methods ===

  /**
   * Get all email ingestion configurations
   */
  async getEmailIngestionConfigs(): Promise<{
    success: boolean;
    data: EmailIngestionConfigSummary[];
  }> {
    return this.fetchApi('/email-ingestion/configs');
  }

  /**
   * Get specific email ingestion configuration
   */
  async getEmailIngestionConfig(configId: number): Promise<{
    success: boolean;
    data: EmailIngestionConfig;
  }> {
    return this.fetchApi(`/email-ingestion/configs/${configId}`);
  }

  /**
   * Create new email ingestion configuration
   */
  async createEmailIngestionConfig(configData: {
    name: string;
    description?: string;
    connection: {
      email_address: string;
      folder_name: string;
    };
    filter_rules?: Array<{
      field: string;
      operation: string;
      value: string;
      case_sensitive: boolean;
    }>;
    monitoring: {
      poll_interval_seconds: number;
      max_backlog_hours: number;
      error_retry_attempts: number;
    };
    created_by: string;
  }): Promise<{
    success: boolean;
    config_id: number;
    message: string;
  }> {
    return this.fetchApi('/email-ingestion/configs', {
      method: 'POST',
      body: JSON.stringify(configData),
    });
  }

  /**
   * Update email ingestion configuration (filter rules only)
   */
  async updateEmailIngestionConfig(configId: number, updateData: {
    description?: string;
    filter_rules?: Array<{
      field: string;
      operation: string;
      value: string;
      case_sensitive: boolean;
    }>;
    monitoring?: {
      poll_interval_seconds: number;
      max_backlog_hours: number;
      error_retry_attempts: number;
    };
  }): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.fetchApi(`/email-ingestion/configs/${configId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    });
  }

  /**
   * Delete email ingestion configuration
   */
  async deleteEmailIngestionConfig(configId: number): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.fetchApi(`/email-ingestion/configs/${configId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Activate email ingestion configuration
   */
  async activateEmailIngestionConfig(configId: number, autoStart: boolean = false): Promise<{
    success: boolean;
    config_id: number;
    config_name: string;
    message: string;
    activated: boolean;
    auto_started?: boolean;
    start_error?: string;
  }> {
    return this.fetchApi(`/email-ingestion/configs/${configId}/activate`, {
      method: 'POST',
      body: JSON.stringify({ auto_start: autoStart }),
    });
  }

  /**
   * Start email ingestion service
   */
  async startEmailIngestionService(): Promise<{
    success: boolean;
    message: string;
    config_id?: number;
    folder_name?: string;
    cursor_id?: number;
  }> {
    return this.fetchApi('/email-ingestion/start', {
      method: 'POST',
    });
  }

  /**
   * Stop email ingestion service
   */
  async stopEmailIngestionService(): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.fetchApi('/email-ingestion/stop', {
      method: 'POST',
    });
  }

  /**
   * Get email ingestion service status
   */
  async getEmailIngestionStatus(): Promise<{
    success: boolean;
    data: EmailIngestionStatus;
  }> {
    return this.fetchApi('/email-ingestion/status');
  }

  /**
   * Get processed emails
   */
  async getProcessedEmails(params?: {
    page?: number;
    limit?: number;
    folder?: string;
  }): Promise<{
    success: boolean;
    data: ProcessedEmail[];
    total: number;
  }> {
    const searchParams = new URLSearchParams();
    
    if (params?.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params?.limit) {
      searchParams.append('limit', params.limit.toString());
    }
    if (params?.folder) {
      searchParams.append('folder', params.folder);
    }

    const endpoint = `/email-ingestion/emails${searchParams.toString() ? `?${searchParams}` : ''}`;
    return this.fetchApi(endpoint);
  }

  /**
   * Test Outlook folder connection
   */
  async testOutlookFolders(emailAddress?: string): Promise<{
    success: boolean;
    data: {
      folders: Array<{
        account: string;
        folders: Array<{
          name: string;
          display_name?: string;
          path: string;
          type: 'standard' | 'custom' | 'folder';
          count: number;
        }>;
      }>;
      total_accounts: number;
    };
  }> {
    const endpoint = `/email-ingestion/test/folders${emailAddress ? `?email_address=${encodeURIComponent(emailAddress)}` : ''}`;
    return this.fetchApi(endpoint);
  }

  /**
   * Discover available email accounts from Outlook
   */
  async discoverEmailAccounts(): Promise<{
    success: boolean;
    data: {
      emails: Array<{
        email_address: string;
        display_name: string;
        account_type: number;
        is_default: boolean;
      }>;
      total_accounts: number;
    };
  }> {
    return this.fetchApi('/email-ingestion/discover/emails');
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

// Types are exported as part of the interface definitions above