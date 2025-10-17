/**
 * Mock data for ETO runs API
 */

import {
  EtoRunListItem,
  EtoRunDetail,
  EtoRunStatus,
} from '../types';
import {
  GetEtoRunsResponse,
  PostEtoRunUploadResponse,
} from '../api/types';

// =============================================================================
// Helper Functions
// =============================================================================

// Actual file sizes from client-new/public/data/pdfs/
const actualFileSizes: Record<number, number> = {
  2: 93748,    // 2.pdf
  3: 174689,   // 3.pdf
  4: 205522,   // 4.pdf
  103: 112450, // 103.pdf
};

const createMockPdfInfo = (id: number, filename: string) => ({
  id,
  original_filename: filename,
  file_size: actualFileSizes[id] || Math.floor(Math.random() * 200000) + 100000,
});

const createMockEmailSource = (senderEmail: string) => ({
  type: 'email' as const,
  sender_email: senderEmail,
  received_date: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
  subject: 'ETO Document Received',
  folder_name: 'Inbox',
});

const createMockManualSource = () => ({
  type: 'manual' as const,
});

const createMockTemplate = (id: number, name: string) => ({
  template_id: id,
  template_name: name,
  version_id: id * 10,
  version_num: 1,
});

// =============================================================================
// Mock List Items (one for each status)
// =============================================================================

// Use actual PDF IDs from client-new/public/data/pdfs/ (2.pdf, 3.pdf, 4.pdf, 103.pdf)

export const mockNotStartedRun: EtoRunListItem = {
  id: 1,
  status: 'not_started',
  processing_step: null,
  started_at: null,
  completed_at: null,
  error_type: null,
  error_message: null,
  pdf: createMockPdfInfo(2, '2.pdf'),
  source: createMockEmailSource('sender1@example.com'),
  matched_template: null,
};

export const mockProcessingRun: EtoRunListItem = {
  id: 2,
  status: 'processing',
  processing_step: 'data_extraction',
  started_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 mins ago
  completed_at: null,
  error_type: null,
  error_message: null,
  pdf: createMockPdfInfo(3, '3.pdf'),
  source: createMockEmailSource('sender2@example.com'),
  matched_template: createMockTemplate(1, 'Standard HAWB Template'),
};

export const mockSuccessRun: EtoRunListItem = {
  id: 3,
  status: 'success',
  processing_step: null,
  started_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(), // 1 hour ago
  completed_at: new Date(Date.now() - 50 * 60 * 1000).toISOString(), // 50 mins ago
  error_type: null,
  error_message: null,
  pdf: createMockPdfInfo(103, '103.pdf'),
  source: createMockEmailSource('sender3@example.com'),
  matched_template: createMockTemplate(1, 'Standard HAWB Template'),
};

export const mockFailureRun: EtoRunListItem = {
  id: 4,
  status: 'failure',
  processing_step: 'data_extraction',
  started_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
  completed_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 30000).toISOString(),
  error_type: 'ExtractionError',
  error_message: 'Failed to extract required field: customer_name',
  pdf: createMockPdfInfo(4, '4.pdf'),
  source: createMockManualSource(),
  matched_template: createMockTemplate(2, 'Alternative HAWB Template'),
};

export const mockNeedsTemplateRun: EtoRunListItem = {
  id: 5,
  status: 'needs_template',
  processing_step: 'template_matching',
  started_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(), // 3 hours ago
  completed_at: new Date(Date.now() - 3 * 60 * 60 * 1000 + 5000).toISOString(),
  error_type: 'TemplateMatchingError',
  error_message: 'No matching template found for this PDF',
  pdf: createMockPdfInfo(2, '2.pdf'),
  source: createMockEmailSource('sender5@example.com'),
  matched_template: null,
};

export const mockSkippedRun: EtoRunListItem = {
  id: 6,
  status: 'skipped',
  processing_step: null,
  started_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
  completed_at: null,
  error_type: null,
  error_message: null,
  pdf: createMockPdfInfo(3, '3.pdf'),
  source: createMockEmailSource('sender6@example.com'),
  matched_template: null,
};

// Additional runs for variety
export const mockSuccessRun2: EtoRunListItem = {
  id: 7,
  status: 'success',
  processing_step: null,
  started_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
  completed_at: new Date(Date.now() - 3.5 * 60 * 60 * 1000).toISOString(),
  error_type: null,
  error_message: null,
  pdf: createMockPdfInfo(4, '4.pdf'),
  source: createMockManualSource(),
  matched_template: createMockTemplate(1, 'Standard HAWB Template'),
};

export const mockFailureRun2: EtoRunListItem = {
  id: 8,
  status: 'failure',
  processing_step: 'data_transformation',
  started_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
  completed_at: new Date(Date.now() - 4.8 * 60 * 60 * 1000).toISOString(),
  error_type: 'PipelineExecutionError',
  error_message: 'Pipeline execution failed at step 3: Invalid data format',
  pdf: createMockPdfInfo(103, '103.pdf'),
  source: createMockEmailSource('sender8@example.com'),
  matched_template: createMockTemplate(2, 'Alternative HAWB Template'),
};

export const mockNotStartedRun2: EtoRunListItem = {
  id: 9,
  status: 'not_started',
  processing_step: null,
  started_at: null,
  completed_at: null,
  error_type: null,
  error_message: null,
  pdf: createMockPdfInfo(2, '2.pdf'),
  source: createMockManualSource(),
  matched_template: null,
};

export const mockSkippedRun2: EtoRunListItem = {
  id: 10,
  status: 'skipped',
  processing_step: null,
  started_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  completed_at: null,
  error_type: null,
  error_message: null,
  pdf: createMockPdfInfo(3, '3.pdf'),
  source: createMockEmailSource('sender10@example.com'),
  matched_template: null,
};

// =============================================================================
// Grouped Mock Data by Status
// =============================================================================

export const mockRunsByStatus: Record<EtoRunStatus, EtoRunListItem[]> = {
  not_started: [mockNotStartedRun, mockNotStartedRun2],
  processing: [mockProcessingRun],
  success: [mockSuccessRun, mockSuccessRun2],
  failure: [mockFailureRun, mockFailureRun2],
  needs_template: [mockNeedsTemplateRun],
  skipped: [mockSkippedRun, mockSkippedRun2],
};

export const allMockRuns: EtoRunListItem[] = [
  mockNotStartedRun,
  mockProcessingRun,
  mockSuccessRun,
  mockFailureRun,
  mockNeedsTemplateRun,
  mockSkippedRun,
  mockSuccessRun2,
  mockFailureRun2,
  mockNotStartedRun2,
  mockSkippedRun2,
];

// =============================================================================
// Mock List Response
// =============================================================================

export const mockGetEtoRunsResponse: GetEtoRunsResponse = {
  items: allMockRuns,
  total: allMockRuns.length,
  limit: 50,
  offset: 0,
};

// =============================================================================
// Mock Detail Response (for successful run)
// =============================================================================

export const mockSuccessRunDetail: EtoRunDetail = {
  ...mockSuccessRun,
  pdf: {
    ...mockSuccessRun.pdf,
    page_count: 3,
  },
  template_matching: {
    status: 'success',
    started_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 59 * 60 * 1000).toISOString(),
    error_message: null,
    matched_template: createMockTemplate(1, 'Standard HAWB Template'),
  },
  data_extraction: {
    status: 'success',
    started_at: new Date(Date.now() - 59 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 55 * 60 * 1000).toISOString(),
    error_message: null,
    extracted_data: {
      hawb_number: 'HAWB-2024-12345',
      customer_name: 'Acme Corporation',
      origin: 'LAX',
      destination: 'JFK',
      weight: '150.5',
      pieces: '10',
      date: '2024-10-15',
    },
  },
  pipeline_execution: {
    status: 'success',
    started_at: new Date(Date.now() - 55 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 50 * 60 * 1000).toISOString(),
    error_message: null,
    executed_actions: [
      {
        action_module_name: 'Send Email',
        inputs: {
          to: 'warehouse@acme.com',
          subject: 'New HAWB Received',
          body: 'HAWB-2024-12345 has been processed',
        },
      },
      {
        action_module_name: 'Create File',
        inputs: {
          filename: 'hawb_2024_12345.json',
          content: '{"hawb": "HAWB-2024-12345", "customer": "Acme Corporation"}',
        },
      },
    ],
    steps: [
      {
        id: 301,
        step_number: 1,
        module_instance_id: 'transform_1',
        inputs: {
          input_data: {
            value: { hawb_number: 'HAWB-2024-12345' },
            type: 'object',
          },
        },
        outputs: {
          transformed_data: {
            value: { hawb: 'HAWB-2024-12345' },
            type: 'object',
          },
        },
        error: null,
      },
      {
        id: 302,
        step_number: 2,
        module_instance_id: 'action_email_1',
        inputs: {
          recipient: { value: 'warehouse@acme.com', type: 'string' },
          message: { value: 'New HAWB Received', type: 'string' },
        },
        outputs: {
          success: { value: true, type: 'boolean' },
        },
        error: null,
      },
    ],
  },
};

// =============================================================================
// Mock Upload Response
// =============================================================================

export const mockUploadResponse: PostEtoRunUploadResponse = {
  id: 11,
  pdf_file_id: 4, // Use actual PDF ID
  status: 'not_started',
  processing_step: null,
  started_at: null,
  completed_at: null,
};

// =============================================================================
// Mock Detail Responses by ID
// =============================================================================

export const mockRunDetailsById: Record<number, EtoRunDetail> = {
  3: mockSuccessRunDetail,
  // Add more as needed
};
