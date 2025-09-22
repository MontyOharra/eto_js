/**
 * PDF Templates API Client
 * Matches FastAPI router: /api/pdf_templates
 */

import { BaseApiClient } from '../base/apiClient';

// Types matching the FastAPI backend models exactly

export interface PdfObject {
  type: string;
  page: number;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  bbox?: number[];
  font_name?: string;
  font_size?: number;
  char_count?: number;
}

export interface ExtractionField {
  label: string;
  bounding_box: number[]; // [x0, y0, x1, y1]
  page: number;
  required: boolean;
  validation_regex?: string;
  description?: string;
}

export interface PdfTemplateBase {
  name: string;
  description?: string;
  source_pdf_id: number;
  status: 'active' | 'inactive';
}

export interface PdfTemplateCreate extends PdfTemplateBase {
  initial_signature_objects: PdfObject[];
  initial_extraction_fields: ExtractionField[];
}

export interface PdfTemplateUpdate {
  name?: string;
  description?: string;
  status?: 'active' | 'inactive';
}

export interface PdfTemplate extends PdfTemplateBase {
  id: number;
  current_version_id?: number;
  created_at: string;
  updated_at: string;
}

export interface PdfTemplateVersionBase {
  pdf_template_id: number;
  signature_objects: PdfObject[];
  extraction_fields: ExtractionField[];
  signature_object_count: number;
}

export interface PdfTemplateVersionCreate extends PdfTemplateVersionBase {}

export interface PdfTemplateVersion extends PdfTemplateVersionBase {
  id: number;
  version_num: number;
  usage_count: number;
  last_used_at?: string;
  created_at: string;
}

export interface ServiceStatusResponse {
  service: string;
  status: 'up' | 'down';
  message: string;
}

// Request schemas that match the backend expectations
export interface PdfTemplateVersionCreateRequest {
  signature_objects: PdfObject[];
  extraction_fields: ExtractionField[];
  signature_object_count: number;
}

// Query parameter interfaces
export interface TemplateListFilters {
  template_status?: 'active' | 'inactive';
  order_by?: string;
  desc?: boolean;
  page?: number;
  limit?: number;
}

/**
 * PDF Templates API client
 * Prefix: /api/pdf_templates
 */
export class PdfTemplatesApiClient extends BaseApiClient {
  /**
   * Create new PDF template
   * POST /api/pdf_templates/
   */
  async createTemplate(template: PdfTemplateCreate): Promise<PdfTemplate> {
    return this.post<PdfTemplate>('/api/pdf_templates/', template);
  }

  /**
   * Create new version of PDF template
   * POST /api/pdf_templates/{template_id}/versions
   */
  async createTemplateVersion(
    templateId: number,
    request: PdfTemplateVersionCreateRequest
  ): Promise<PdfTemplateVersion> {
    return this.post<PdfTemplateVersion>(`/api/pdf_templates/${templateId}/versions`, request);
  }

  /**
   * List PDF templates with filtering and pagination
   * GET /api/pdf_templates/
   */
  async getTemplates(filters?: TemplateListFilters): Promise<PdfTemplate[]> {
    let endpoint = '/api/pdf_templates/';

    if (filters) {
      const params = new URLSearchParams();

      if (filters.template_status) params.append('template_status', filters.template_status);
      if (filters.order_by) params.append('order_by', filters.order_by);
      if (filters.desc !== undefined) params.append('desc', filters.desc.toString());
      if (filters.page) params.append('page', filters.page.toString());
      if (filters.limit) params.append('limit', filters.limit.toString());

      const queryString = params.toString();
      if (queryString) {
        endpoint += '?' + queryString;
      }
    }

    return this.get<PdfTemplate[]>(endpoint);
  }

  /**
   * Get specific PDF template by ID
   * GET /api/pdf_templates/{template_id}
   */
  async getTemplate(templateId: number): Promise<PdfTemplate> {
    return this.get<PdfTemplate>(`/api/pdf_templates/${templateId}`);
  }

  /**
   * Get specific template version
   * GET /api/pdf_templates/{template_id}/versions/{version_id}
   */
  async getTemplateVersion(templateId: number, versionId: number): Promise<PdfTemplateVersion> {
    return this.get<PdfTemplateVersion>(`/api/pdf_templates/${templateId}/versions/${versionId}`);
  }

  /**
   * Update PDF template
   * PATCH /api/pdf_templates/{template_id}
   */
  async updateTemplate(templateId: number, update: PdfTemplateUpdate): Promise<PdfTemplate> {
    return this.patch<PdfTemplate>(`/api/pdf_templates/${templateId}`, update);
  }

  /**
   * Get PDF templates service status
   * GET /api/pdf_templates/status
   */
  async getServiceStatus(): Promise<ServiceStatusResponse> {
    return this.get<ServiceStatusResponse>('/api/pdf_templates/status');
  }
}