/**
 * ETO System Type Definitions
 * Updated to match backend API schema
 */

// Core ETO Run interface matching backend API response
export interface EtoRun {
  id: number;
  email_id: number;
  pdf_file_id: number;
  status: "not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped";
  processing_step?: "template_matching" | "extracting_data" | "transforming_data";
  matched_template_id?: number;
  has_extracted_data?: boolean;
  has_transformation_audit?: boolean;
  has_target_data?: boolean;
  error_type?: string;
  error_message?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  
  // Nested objects from backend
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

// Frontend-friendly summary interface for table display
export interface EtoRunSummary {
  id: number;
  fileName: string;
  status: "not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped";
  processing_step?: "template_matching" | "extracting_data" | "transforming_data";
  receivedAt: Date;
  processingCompletedAt?: Date;
  matchedTemplateId?: number;
  hasExtractedData?: boolean;
  hasTransformationAudit?: boolean;
  hasTargetData?: boolean;
  errorMessage?: string;
  emailSubject: string;
  senderEmail: string;
  fileSize: number;
  fileSizeFormatted: string;
}

// Template interface matching backend schema
export interface Template {
  id: number;
  name: string;
  customer_name?: string;
  description?: string;
  status: "active" | "archived" | "draft";
  is_complete: boolean;
  coverage_threshold: number;
  usage_count: number;
  last_used_at?: Date;
  success_rate?: number;
  version: number;
  created_by?: string;
  created_at?: Date;
  updated_at?: Date;
  extraction_rules_count: number;
  signature_object_count: number;
}

// Template summary for list display
export interface TemplateSummary {
  id: number;
  name: string;
  customer_name?: string;
  description?: string;
  status: "active" | "archived" | "draft";
  is_complete: boolean;
  usage_count: number;
  success_rate?: number;
  last_used_at?: Date;
  extraction_rules_count: number;
  created_at?: Date;
  updated_at?: Date;
}

// System statistics interface
export interface SystemStats {
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

// Email service status
export interface EmailServiceStatus {
  monitoring: boolean;
  current_email?: string;
  current_folder?: string;
  connected: boolean;
  last_check?: string;
  error?: string;
}

// Utility functions for data transformation
export class EtoDataTransforms {
  /**
   * Convert backend API EtoRun to frontend summary format
   */
  static toSummary(apiRun: EtoRun): EtoRunSummary {
    return {
      id: apiRun.id,
      fileName: apiRun.pdf_file.original_filename,
      status: apiRun.status,
      processing_step: apiRun.processing_step,
      receivedAt: new Date(apiRun.email.received_date),
      processingCompletedAt: apiRun.completed_at ? new Date(apiRun.completed_at) : undefined,
      matchedTemplateId: apiRun.matched_template_id,
      hasExtractedData: apiRun.has_extracted_data,
      hasTransformationAudit: apiRun.has_transformation_audit,
      hasTargetData: apiRun.has_target_data,
      errorMessage: apiRun.error_message,
      emailSubject: apiRun.email.subject,
      senderEmail: apiRun.email.sender_email,
      fileSize: apiRun.pdf_file.file_size,
      fileSizeFormatted: this.formatFileSize(apiRun.pdf_file.file_size),
    };
  }

  /**
   * Format file size in human-readable format
   */
  static formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }

  /**
   * Format processing duration
   */
  static formatProcessingTime(startTime?: string, endTime?: string): string {
    if (!startTime || !endTime) return 'N/A';
    
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMs = end.getTime() - start.getTime();
    
    if (durationMs < 1000) {
      return `${durationMs}ms`;
    } else if (durationMs < 60000) {
      return `${(durationMs / 1000).toFixed(1)}s`;
    } else {
      return `${(durationMs / 60000).toFixed(1)}m`;
    }
  }

  /**
   * Get status color class for UI
   */
  static getStatusColorClass(status: EtoRun['status']): string {
    switch (status) {
      case 'success':
        return 'text-green-400';
      case 'failure':
        return 'text-red-400';
      case 'needs_template':
        return 'text-yellow-400';
      case 'processing':
        return 'text-blue-400';
      case 'not_started':
        return 'text-gray-400';
      case 'skipped':
        return 'text-gray-500';
      default:
        return 'text-gray-400';
    }
  }

  /**
   * Get status display name
   */
  static getStatusDisplayName(status: EtoRun['status']): string {
    switch (status) {
      case 'success':
        return 'Success';
      case 'failure':
        return 'Failed';
      case 'needs_template':
        return 'Needs Template';
      case 'processing':
        return 'Processing';
      case 'not_started':
        return 'Not Started';
      case 'skipped':
        return 'Skipped';
      default:
        return 'Unknown';
    }
  }

  /**
   * Get processing step display name
   */
  static getProcessingStepDisplayName(step?: EtoRun['processing_step']): string {
    if (!step) return '';
    
    switch (step) {
      case 'template_matching':
        return 'Template Matching';
      case 'extracting_data':
        return 'Extracting Data';
      case 'transforming_data':
        return 'Transforming Data';
      default:
        return step;
    }
  }

  /**
   * Get processing step color class
   */
  static getProcessingStepColorClass(step?: EtoRun['processing_step']): string {
    if (!step) return 'text-gray-400';
    
    switch (step) {
      case 'template_matching':
        return 'text-blue-400';
      case 'extracting_data':
        return 'text-purple-400';
      case 'transforming_data':
        return 'text-indigo-400';
      default:
        return 'text-gray-400';
    }
  }

  /**
   * Convert backend API Template to frontend format
   */
  static templateApiToFrontend(apiTemplate: any): Template {
    return {
      id: apiTemplate.id,
      name: apiTemplate.name,
      customer_name: apiTemplate.customer_name,
      description: apiTemplate.description,
      status: apiTemplate.status,
      is_complete: apiTemplate.is_complete,
      coverage_threshold: apiTemplate.coverage_threshold,
      usage_count: apiTemplate.usage_count,
      last_used_at: apiTemplate.last_used_at ? new Date(apiTemplate.last_used_at) : undefined,
      success_rate: apiTemplate.success_rate,
      version: apiTemplate.version,
      created_by: apiTemplate.created_by,
      created_at: apiTemplate.created_at ? new Date(apiTemplate.created_at) : undefined,
      updated_at: apiTemplate.updated_at ? new Date(apiTemplate.updated_at) : undefined,
      extraction_rules_count: apiTemplate.extraction_rules_count,
      signature_object_count: apiTemplate.signature_object_count,
    };
  }

  /**
   * Convert Template to TemplateSummary for list display
   */
  static templateToSummary(template: Template): TemplateSummary {
    return {
      id: template.id,
      name: template.name,
      customer_name: template.customer_name,
      description: template.description,
      status: template.status,
      is_complete: template.is_complete,
      usage_count: template.usage_count,
      success_rate: template.success_rate,
      last_used_at: template.last_used_at,
      extraction_rules_count: template.extraction_rules_count,
      created_at: template.created_at,
      updated_at: template.updated_at,
    };
  }

  /**
   * Get template status color class
   */
  static getTemplateStatusColor(status: Template['status']): string {
    switch (status) {
      case 'active':
        return 'text-green-400';
      case 'draft':
        return 'text-yellow-400';
      case 'archived':
        return 'text-gray-400';
      default:
        return 'text-gray-400';
    }
  }

  /**
   * Get template completeness indicator color
   */
  static getTemplateCompletenessColor(isComplete: boolean): string {
    return isComplete ? 'text-green-400' : 'text-orange-400';
  }
}

// Export all types
export type { 
  EtoRun, 
  EtoRunSummary, 
  Template, 
  TemplateSummary,
  SystemStats, 
  EmailServiceStatus 
};