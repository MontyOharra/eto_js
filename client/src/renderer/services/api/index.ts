/**
 * Unified API Client for ETO FastAPI Backend
 * Domain-based API client architecture
 */

// Base client and utilities
export { BaseApiClient, ApiError } from './base/apiClient';

// Domain-specific API clients
export { HealthApiClient } from './domains/health';
export { EmailConfigsApiClient } from './domains/emailConfigs';
export { PdfTemplatesApiClient } from './domains/pdfTemplates';

// Type exports for convenience
export type {
  // Health types
  BasicHealthResponse,
  DetailedServiceStatus,
  ReadinessResponse,
  ServiceStatusDetail,
  DatabaseStatus,
  StorageStatus,
} from './domains/health';

export type {
  // Email config types
  EmailFilterRule,
  EmailConfigBase,
  EmailConfig,
  EmailConfigCreate,
  EmailConfigUpdate,
  EmailAccount,
  EmailFolder,
  ActivationResponse,
} from './domains/emailConfigs';

export type {
  // PDF template types
  PdfObject,
  ExtractionField,
  PdfTemplateBase,
  PdfTemplateCreate,
  PdfTemplateUpdate,
  PdfTemplate,
  PdfTemplateVersionBase,
  PdfTemplateVersionCreate,
  PdfTemplateVersion,
  PdfTemplateVersionCreateRequest,
  TemplateListFilters,
} from './domains/pdfTemplates';

/**
 * Unified API client that provides access to all domain-specific clients
 */
export class EtoApiClient {
  public health: HealthApiClient;
  public emailConfigs: EmailConfigsApiClient;
  public pdfTemplates: PdfTemplatesApiClient;

  constructor(baseUrl: string = 'http://localhost:8080') {
    this.health = new HealthApiClient(baseUrl);
    this.emailConfigs = new EmailConfigsApiClient(baseUrl);
    this.pdfTemplates = new PdfTemplatesApiClient(baseUrl);
  }

  /**
   * Test if the API server is reachable
   */
  async ping(): Promise<boolean> {
    try {
      await this.health.getHealth();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get overall system health status
   */
  async getSystemHealth(): Promise<DetailedServiceStatus> {
    return this.health.getServiceStatus();
  }
}

// Default instance for convenience
export const apiClient = new EtoApiClient();