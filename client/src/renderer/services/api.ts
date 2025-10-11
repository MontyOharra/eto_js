/**
 * API Client for ETO Backend Service
 * Handles all HTTP communication with the Flask backend
 */

// Backend API Response Types - Updated for new unified server
export interface ApiEtoRunSummary {
  id: number;
  pdf_file_id: number;
  status: "not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped";
  processing_step?: "template_matching" | "extracting_data" | "transforming_data";

  // Basic metadata
  pdf_filename: string;
  file_size: number;

  // Processing info
  matched_template_id?: number;
  matched_template_name?: string;
  processing_duration_ms?: number;
  error_message?: string;

  // Timestamps
  created_at: string;
  started_at?: string;
  completed_at?: string;

  // Email information (when PDF originated from email ingestion)
  email?: {
    email_id: number;
    subject?: string;
    sender_email?: string;
    sender_name?: string;
    received_at?: string;
  };
}

// Full ETO run details (for individual run endpoint)
export interface ApiEtoRun extends ApiEtoRunSummary {
  // Additional detailed fields for full run object
  extracted_data?: any;
  transformation_audit?: any;
  target_data?: any;
  error_details?: any;
  step_execution_log?: any;
}

// Response is direct array from FastAPI
export interface ApiEtoRunsResponse {
  // New server returns array directly, not wrapped in response object
  data: ApiEtoRunSummary[];
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

// Email Ingestion Types - matching backend EmailConfig model
export interface EmailIngestionConfig {
  id: number;
  name: string;
  description?: string;
  email_address: string;
  folder_name: string;
  filter_rules: Array<{
    field: string;
    operation: string;
    value: string;
    case_sensitive: boolean;
  }>;
  poll_interval_seconds: number;
  max_backlog_hours: number;
  error_retry_attempts: number;
  is_active: boolean;
  is_running: boolean;
  emails_processed: number;
  pdfs_found: number;
  last_error_message?: string;
  last_error_at?: string;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
  activated_at?: string;
  last_check_time?: string;
  total_emails_processed: number;
  total_pdfs_found: number;
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



// API Configuration - Updated for unified ETO server
const API_BASE_URL = 'http://localhost:8090';

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
    return this.fetchApi('/api/health');
  }

  /**
   * Get ETO Service Health
   */
  async getEtoHealth(): Promise<{
    status: string;
    service_name: string;
    timestamp: string;
    worker: {
      worker_enabled: boolean;
      worker_running: boolean;
      worker_paused: boolean;
      max_concurrent_runs: number;
      polling_interval: number;
      pending_runs_count: number;
      currently_processing_count: number;
      worker_task_active: boolean;
    };
    details: {
      processing_enabled: boolean;
      database_connected: boolean;
      template_service_available: boolean;
      background_processing: boolean;
    };
  }> {
    return this.fetchApi('/api/eto-runs/health');
  }

  /**
   * Get ETO Runs - Updated for new unified server
   */
  async getEtoRuns(params?: {
    eto_run_status?: string; // Updated parameter name
    limit?: number;
    offset?: number;
    order_by?: string;
    order_direction?: string;
    since_date?: string;
  }): Promise<{ data: ApiEtoRunSummary[] }> {
    const searchParams = new URLSearchParams();

    if (params?.eto_run_status) {
      searchParams.append('eto_run_status', params.eto_run_status);
    }
    if (params?.limit) {
      searchParams.append('limit', params.limit.toString());
    }
    if (params?.offset) {
      searchParams.append('offset', params.offset.toString());
    }
    if (params?.order_by) {
      searchParams.append('order_by', params.order_by);
    }
    if (params?.order_direction) {
      searchParams.append('order_direction', params.order_direction);
    }
    if (params?.since_date) {
      searchParams.append('since_date', params.since_date);
    }

    const endpoint = `/api/eto-runs${searchParams.toString() ? `?${searchParams}` : ''}`;
    const data = await this.fetchApi<ApiEtoRunSummary[]>(endpoint);
    return { data };
  }

  /**
   * Get ETO Run Details
   */
  async getEtoRunDetails(runId: string | number): Promise<{ data: ApiEtoRun }> {
    const data = await this.fetchApi<ApiEtoRun>(`/api/eto-runs/${runId}`);
    return { data };
  }

  /**
   * Skip ETO Run
   */
  async skipEtoRun(runId: string | number, params?: {
    reason?: string;
    permanent?: boolean;
  }): Promise<{ success: boolean; data: ApiEtoRun }> {
    const data = await this.fetchApi<ApiEtoRun>(`/api/eto-runs/${runId}/skip`, {
      method: 'PATCH',
      body: params ? JSON.stringify(params) : undefined,
    });
    return { success: true, data };
  }

  /**
   * Delete ETO Run
   */
  async deleteEtoRun(runId: string | number): Promise<{ success: boolean; data: ApiEtoRun }> {
    const data = await this.fetchApi<ApiEtoRun>(`/api/eto-runs/${runId}`, {
      method: 'DELETE',
    });
    return { success: true, data };
  }

  /**
   * Reprocess ETO Run
   */
  async reprocessEtoRun(runId: string | number, params?: {
    force?: boolean;
  }): Promise<{ success: boolean; data: ApiEtoRun }> {
    const searchParams = new URLSearchParams();
    if (params?.force) {
      searchParams.append('force', params.force.toString());
    }

    const endpoint = `/api/eto-runs/${runId}/reprocess${searchParams.toString() ? `?${searchParams}` : ''}`;
    const data = await this.fetchApi<ApiEtoRun>(endpoint, {
      method: 'PATCH',
    });
    return { success: true, data };
  }

  /**
   * Get ETO Worker Status
   */
  async getEtoWorkerStatus(): Promise<{
    worker_enabled: boolean;
    worker_running: boolean;
    worker_paused: boolean;
    max_concurrent_runs: number;
    polling_interval: number;
    pending_runs_count: number;
    currently_processing_count: number;
    worker_task_active: boolean;
    timestamp: string;
  }> {
    return this.fetchApi('/api/eto-runs/worker/status');
  }

  /**
   * Start ETO Worker
   */
  async startEtoWorker(): Promise<{
    action: string;
    success: boolean;
    message: string;
    timestamp: string;
  }> {
    return this.fetchApi('/api/eto-runs/worker/start', {
      method: 'POST',
    });
  }

  /**
   * Stop ETO Worker
   */
  async stopEtoWorker(graceful: boolean = true): Promise<{
    action: string;
    success: boolean;
    graceful: boolean;
    message: string;
    timestamp: string;
  }> {
    const searchParams = new URLSearchParams();
    searchParams.append('graceful', graceful.toString());

    return this.fetchApi(`/api/eto-runs/worker/stop?${searchParams}`, {
      method: 'POST',
    });
  }

  /**
   * Pause ETO Worker
   */
  async pauseEtoWorker(): Promise<{
    action: string;
    success: boolean;
    message: string;
    timestamp: string;
  }> {
    return this.fetchApi('/api/eto-runs/worker/pause', {
      method: 'POST',
    });
  }

  /**
   * Resume ETO Worker
   */
  async resumeEtoWorker(): Promise<{
    action: string;
    success: boolean;
    message: string;
    timestamp: string;
  }> {
    return this.fetchApi('/api/eto-runs/worker/resume', {
      method: 'POST',
    });
  }

  /**
   * Get System Statistics
   */
  async getSystemStats(): Promise<ApiSystemStats> {
    return this.fetchApi('/api/health/metrics');
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

    const endpoint = `/api/templates/${searchParams.toString() ? `?${searchParams}` : ''}`;
    return this.fetchApi<ApiTemplatesResponse>(endpoint);
  }

  /**
   * Get PDF File (binary data)
   */
  getPdfFileUrl(pdfId: number): string {
    return `${this.baseUrl}/api/pdfs/${pdfId}`;
  }

  /**
   * Get PDF content URL for an ETO run
   */
  getEtoRunPdfContentUrl(runId: string | number): string {
    return `${this.baseUrl}/api/eto-runs/${runId}/pdf-content`;
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
    run_id: number;
    pdf_id: number;
    filename: string;
    original_filename: string;
    page_count: number;
    object_count: number;
    file_size: number;
    sha256_hash: string;
    pdf_objects: any[];  // PDF objects from pdf_files table
    status: "not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped";
    processing_step?: "template_matching" | "extracting_data" | "transforming_data";
    matched_template_id?: number;
    // Email context (flat structure)
    email_subject: string;
    sender_email: string;
    received_date: string;
    // Processing data
    extracted_data?: any;
    transformation_audit?: any;
    target_data?: any;
    // Timestamps
    created_at?: string;
    started_at?: string;
    completed_at?: string;
    // Error info
    error_type?: string;
    error_message?: string;
  }> {
    const response = await this.fetchApi<{success: boolean, data: any}>(`/api/eto-runs/${runId}/pdf-data`);
    return response.data;
  }

  /**
   * Create Template
   */
  async createTemplate(templateData: {
    name: string;
    description?: string;
    source_pdf_id: number;
    initial_signature_objects: {
      text_words: any[];
      text_lines: any[];
      graphic_rects: any[];
      graphic_lines: any[];
      graphic_curves: any[];
      images: any[];
      tables: any[];
    };
    initial_extraction_fields: any[];
  }): Promise<{
    id: number;
    name: string;
    description?: string;
    source_pdf_id: number;
    status: string;
    created_at: string;
    updated_at: string;
    current_version_id?: number;
  }> {
    return this.fetchApi('/api/pdf_templates/', {
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
   * Trigger Reprocessing of Failed ETO Runs (legacy endpoint)
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
   * Bulk Skip ETO Runs
   */
  async bulkSkipRuns(runIds: number[]): Promise<{
    operation: string;
    total_requested: number;
    successful: number;
    failed: number;
    results: Array<{ run_id: number; status: string; new_status?: string }>;
    errors: Array<{ run_id: number; status: string; error: string }>;
    timestamp: string;
  }> {
    return this.fetchApi('/api/eto-runs/bulk/skip', {
      method: 'PATCH',
      body: JSON.stringify({ run_ids: runIds }),
    });
  }


  /**
   * Queue PDF for ETO Processing
   */
  async queuePdfProcessing(pdfFileId: number): Promise<{ data: ApiEtoRun }> {
    const data = await this.fetchApi<ApiEtoRun>(`/api/eto-runs/process-pdf/${pdfFileId}`, {
      method: 'POST',
    });
    return { data };
  }

  /**
   * Bulk reprocess specific runs by IDs
   */
  async reprocessSelectedRuns(runIds: number[]): Promise<{
    operation: string;
    total_requested: number;
    successful: number;
    failed: number;
    results: Array<{ run_id: number; status: string; new_status?: string }>;
    errors: Array<{ run_id: number; status: string; error: string }>;
    timestamp: string;
  }> {
    return this.fetchApi('/api/eto-runs/reprocess-selected', {
      method: 'PATCH',
      body: JSON.stringify({ run_ids: runIds }),
    });
  }

  async reprocessBulkFailedRuns(): Promise<{
    operation: string;
    total_found: number;
    total_reprocessed: number;
    failed_count: number;
    needs_template_count: number;
    skipped_count: number;
    message: string;
    timestamp: string;
  }> {
    return this.fetchApi('/api/eto-runs/reprocess-bulk', {
      method: 'PATCH',
    });
  }

  /**
   * Reprocess single run (convenience method using bulk endpoint)
   */
  async reprocessSingleRun(runId: number): Promise<{
    operation: string;
    total_requested: number;
    successful: number;
    failed: number;
    results: Array<{ run_id: number; status: string; new_status?: string }>;
    errors: Array<{ run_id: number; status: string; error: string }>;
    timestamp: string;
  }> {
    return this.reprocessSelectedRuns([runId]);
  }

  /**
   * Reprocess all failed and needs_template runs
   */
  async reprocessAllFailedRuns(): Promise<{
    operation: string;
    total_found: number;
    total_reprocessed: number;
    failed_count: number;
    needs_template_count: number;
    successful_reprocessed: Array<{ run_id: number; original_status: string; new_status: string }>;
    errors: Array<{ run_id: number; original_status: string; error: string }>;
    message: string;
    timestamp: string;
  }> {
    return this.fetchApi('/api/eto-runs/reprocess-failed', {
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

  // === Transformation Pipeline API Methods ===

  /**
   * Create/upload a new pipeline
   */
  async createPipeline(pipelineData: {
    name: string;
    description?: string;
    pipeline_json: any;
    visual_json: any;
  }): Promise<{
    id: string;
    name: string;
    description?: string;
    pipeline_json: any;
    visual_json: any;
    plan_checksum?: string;
    compiled_at?: string;
    created_at: string;
    is_active: boolean;
    module_count: number;
    connection_count: number;
    entry_point_count: number;
  }> {
    return this.fetchApi('/api/pipelines', {
      method: 'POST',
      body: JSON.stringify(pipelineData),
    });
  }

  /**
   * Get all pipelines
   */
  async getPipelines(params?: {
    include_inactive?: boolean;
    summary_only?: boolean;
  }): Promise<{
    pipelines: any[];
    total_count: number;
  }> {
    const searchParams = new URLSearchParams();
    if (params?.include_inactive) {
      searchParams.append('include_inactive', params.include_inactive.toString());
    }
    if (params?.summary_only) {
      searchParams.append('summary_only', params.summary_only.toString());
    }

    const endpoint = `/api/pipelines${searchParams.toString() ? `?${searchParams}` : ''}`;
    return this.fetchApi(endpoint);
  }

  /**
   * Get specific pipeline by ID
   */
  async getPipeline(pipelineId: string): Promise<{
    id: string;
    name: string;
    description?: string;
    pipeline_json: any;
    visual_json: any;
    plan_checksum?: string;
    compiled_at?: string;
    created_at: string;
    is_active: boolean;
    module_count: number;
    connection_count: number;
    entry_point_count: number;
  }> {
    return this.fetchApi(`/api/pipelines/${pipelineId}`);
  }

  // === Email Ingestion API Methods ===

  /**
   * Get all email ingestion configurations
   */
  async getEmailIngestionConfigs(): Promise<{
    success: boolean;
    data: EmailIngestionConfig[];
  }> {
    try {
      const configs = await this.fetchApi<EmailIngestionConfig[]>('/api/email-configs/');

      // Backend returns raw array, wrap in expected format
      return {
        success: true,
        data: configs
      };
    } catch (error) {
      throw error; // Let the calling code handle the error
    }
  }

  /**
   * Get specific email ingestion configuration
   */
  async getEmailIngestionConfig(configId: number): Promise<{
    success: boolean;
    data: EmailIngestionConfig;
  }> {
    try {
      const config = await this.fetchApi<EmailIngestionConfig>(`/api/email-configs/${configId}`);

      // Backend returns raw config object, wrap in expected format
      return {
        success: true,
        data: config
      };
    } catch (error) {
      throw error; // Let the calling code handle the error
    }
  }

  /**
   * Create new email ingestion configuration
   */
  async createEmailIngestionConfig(configData: {
    name: string;
    description?: string;
    email_address: string;
    folder_name: string;
    filter_rules?: Array<{
      field: string;
      operation: string;
      value: string;
      case_sensitive: boolean;
    }>;
    poll_interval_seconds: number;
    max_backlog_hours: number;
    error_retry_attempts: number;
  }): Promise<{
    success: boolean;
    data: any;
  }> {
    try {
      const result = await this.fetchApi('/api/email-configs/', {
        method: 'POST',
        body: JSON.stringify(configData),
      });

      // Backend returns the EmailConfig directly
      return {
        success: true,
        data: result
      };
    } catch (error) {
      throw error; // Let the calling code handle the error
    }
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
    poll_interval_seconds?: number;
    max_backlog_hours?: number;
    error_retry_attempts?: number;
  }): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const updatedConfig = await this.fetchApi<EmailIngestionConfig>(`/api/email-configs/${configId}`, {
        method: 'PUT',
        body: JSON.stringify(updateData),
      });

      // Backend returns updated config object, wrap in expected format
      return {
        success: true,
        message: 'Configuration updated successfully'
      };
    } catch (error) {
      throw error; // Let the calling code handle the error
    }
  }

  /**
   * Delete email ingestion configuration
   */
  async deleteEmailIngestionConfig(configId: number): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.fetchApi(`/api/email-configs/${configId}`, {
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
    return this.fetchApi(`/api/email-configs/${configId}/activate?activate=true`, {
      method: 'PATCH',
    });
  }

  /**
   * Deactivate email ingestion configuration
   */
  async deactivateEmailIngestionConfig(configId: number): Promise<{
    success: boolean;
    config_id: number;
    config_name: string;
    message: string;
    activated: boolean;
  }> {
    return this.fetchApi(`/api/email-configs/${configId}/activate?activate=false`, {
      method: 'PATCH',
    });
  }



  /**
   * Test Outlook folder connection
   */
  async testOutlookFolders(emailAddress?: string): Promise<{
    success: boolean;
    data: {
      folders: Array<{
        name: string;
        display_name?: string;
        folder_id?: string;
        message_count?: number;
      }>;
    };
  }> {
    try {
      const folders = await this.fetchApi<Array<{
        name: string;
        display_name?: string;
        folder_id?: string;
        message_count?: number;
      }>>(`/api/email-configs/discovery/folders${emailAddress ? `?email_address=${encodeURIComponent(emailAddress)}` : ''}`)

      // Wrap the raw array response in the expected format
      return {
        success: true,
        data: {
          folders: folders
        }
      };
    } catch (error) {
      throw error; // Let the calling code handle the error
    }
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
        account_type: string;
        is_default: boolean;
      }>;
      total_accounts: number;
    };
  }> {
    try {
      const accounts = await this.fetchApi<Array<{
        email_address: string;
        display_name: string;
        account_type: string;
        is_default: boolean;
        provider_specific_id?: string;
      }>>('/api/email-configs/discovery/accounts');

      // Wrap the raw array response in the expected format
      return {
        success: true,
        data: {
          emails: accounts,
          total_accounts: accounts.length
        }
      };
    } catch (error) {
      throw error; // Let the calling code handle the error
    }
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

// Export transformation pipeline client instance (different port)
export const pipelineApiClient = new ApiClient('http://localhost:8090');

// Types are exported as part of the interface definitions above