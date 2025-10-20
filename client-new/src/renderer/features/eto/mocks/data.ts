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
import {
  mockPipeline1SuccessExecution,
  mockPipeline2SuccessExecution,
  mockPipeline3FailureExecution,
  mockPipeline1FailureExecution,
  mockPipeline4SuccessExecution,
} from '../../pipelines/mocks/pipelineExecutionMock';

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
  pdf: createMockPdfInfo(2, '2.pdf'),
  source: createMockEmailSource('sender3@example.com'),
  matched_template: createMockTemplate(1, 'Standard HAWB Template'),
};

export const mockFailureRun: EtoRunListItem = {
  id: 4,
  status: 'failure',
  processing_step: 'data_transformation',
  started_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
  completed_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 30000).toISOString(),
  error_type: 'PipelineExecutionError',
  error_message: 'Pipeline execution failed: PermissionError - Unable to write to output stream: permission denied',
  pdf: createMockPdfInfo(4, '4.pdf'),
  source: createMockManualSource(),
  matched_template: createMockTemplate(3, 'Minimal Text Template'),
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
  error_message: 'Pipeline execution failed: TypeError - Expected \'str\' but received \'NoneType\' for parameter \'text\'',
  pdf: createMockPdfInfo(103, '103.pdf'),
  source: createMockEmailSource('sender8@example.com'),
  matched_template: createMockTemplate(1, 'Simple Text Processing Template'),
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

export const mockSuccessRun3: EtoRunListItem = {
  id: 11,
  status: 'success',
  processing_step: null,
  started_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
  completed_at: new Date(Date.now() - 5.8 * 60 * 60 * 1000).toISOString(),
  error_type: null,
  error_message: null,
  pdf: createMockPdfInfo(103, '103.pdf'),
  source: createMockManualSource(),
  matched_template: createMockTemplate(4, 'Complex Order Processing Template'),
};

// =============================================================================
// Grouped Mock Data by Status
// =============================================================================

export const mockRunsByStatus: Record<EtoRunStatus, EtoRunListItem[]> = {
  not_started: [mockNotStartedRun, mockNotStartedRun2],
  processing: [mockProcessingRun],
  success: [mockSuccessRun, mockSuccessRun2, mockSuccessRun3],
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
  mockSuccessRun3,
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
    page_count: 1,
  },
  template_matching: {
    status: 'success',
    started_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 59 * 60 * 1000).toISOString(),
    error_message: null,
    matched_template: createMockTemplate(1, 'Simple Text Processing Template'),
  },
  data_extraction: {
    status: 'success',
    started_at: new Date(Date.now() - 59 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 55 * 60 * 1000).toISOString(),
    error_message: null,
    // Matches pipeline #1 entry point (e1: input_text)
    extracted_data: {
      input_text: '  Hello World  ',
    },
    extracted_fields_with_boxes: [
      {
        field_id: 'input_text',
        label: 'input_text',
        value: '  Hello World  ',
        page: 0,
        bbox: [250, 50, 400, 70],
      },
    ],
  },
  pipeline_execution: {
    status: 'success',
    started_at: new Date(Date.now() - 55 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 50 * 60 * 1000).toISOString(),
    error_message: null,
    pipeline_definition_id: 1,  // Pipeline #1 (Simple)
    executed_actions: [
      {
        action_module_name: 'Print Action',
        inputs: {
          message: 'HELLO WORLD',
          prefix: 'Result: ',
        },
      },
    ],
    steps: mockPipeline1SuccessExecution,
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
// Mock Detail Response for Second Success Run
// =============================================================================

export const mockSuccessRun2Detail: EtoRunDetail = {
  ...mockSuccessRun2,
  pdf: {
    ...mockSuccessRun2.pdf,
    page_count: 2,
  },
  template_matching: {
    status: 'success',
    started_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 3.95 * 60 * 60 * 1000).toISOString(),
    error_message: null,
    matched_template: createMockTemplate(2, 'Complex Multi-Branch HAWB Template'),
  },
  data_extraction: {
    status: 'success',
    started_at: new Date(Date.now() - 3.95 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 3.7 * 60 * 60 * 1000).toISOString(),
    error_message: null,
    // Matches pipeline #2 entry points (e1: hawb, e2: customer, e3: weight, e4: dimensions)
    extracted_data: {
      hawb: '  HAWB-2024-12345  ',
      customer: '  Acme Corporation  ',
      weight: '250.5',
      dimensions: '  48x40x36  ',
    },
    extracted_fields_with_boxes: [
      {
        field_id: 'hawb',
        label: 'hawb',
        value: '  HAWB-2024-12345  ',
        page: 0,
        bbox: [250, 50, 400, 70],
      },
      {
        field_id: 'customer',
        label: 'customer',
        value: '  Acme Corporation  ',
        page: 0,
        bbox: [250, 100, 500, 120],
      },
      {
        field_id: 'weight',
        label: 'weight',
        value: '250.5',
        page: 0,
        bbox: [250, 150, 350, 170],
      },
      {
        field_id: 'dimensions',
        label: 'dimensions',
        value: '  48x40x36  ',
        page: 0,
        bbox: [250, 200, 400, 220],
      },
    ],
  },
  pipeline_execution: {
    status: 'success',
    started_at: new Date(Date.now() - 3.7 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 3.5 * 60 * 60 * 1000).toISOString(),
    error_message: null,
    pipeline_definition_id: 2,  // Pipeline #2 (Complex)
    executed_actions: [
      {
        action_module_name: 'Print Action',
        inputs: {
          message: 'HAWB-2024-12345250.5ACME CORPORATION250.548x40x36  Acme Corporation    HAWB-2024-12345  ',
          prefix: 'Final: ',
        },
      },
    ],
    steps: mockPipeline2SuccessExecution,
  },
};

// =============================================================================
// Mock Detail Response for Processing Run
// =============================================================================

export const mockProcessingRunDetail: EtoRunDetail = {
  ...mockProcessingRun,
  pdf: {
    ...mockProcessingRun.pdf,
    page_count: 4,
  },
  template_matching: {
    status: 'success',
    started_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 4.5 * 60 * 1000).toISOString(),
    error_message: null,
    matched_template: createMockTemplate(1, 'Standard HAWB Template'),
  },
  data_extraction: {
    status: 'processing',
    started_at: new Date(Date.now() - 4.5 * 60 * 1000).toISOString(),
    completed_at: null,
    error_message: null,
    extracted_data: null,
  },
  pipeline_execution: {
    status: 'not_started',
    started_at: null,
    completed_at: null,
    error_message: null,
    pipeline_definition_id: 1,
    executed_actions: null,
    steps: [],
  },
};

// =============================================================================
// Mock Detail Response for Failure Run
// =============================================================================

export const mockFailureRunDetail: EtoRunDetail = {
  ...mockFailureRun,
  pdf: {
    ...mockFailureRun.pdf,
    page_count: 2,
  },
  template_matching: {
    status: 'success',
    started_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 5000).toISOString(),
    error_message: null,
    matched_template: createMockTemplate(3, 'Minimal Text Template'),
  },
  data_extraction: {
    status: 'success',
    started_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 5000).toISOString(),
    completed_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 15000).toISOString(),
    error_message: null,
    // Matches pipeline #3 entry point (e1: text)
    extracted_data: {
      text: 'test input',
    },
    extracted_fields_with_boxes: [
      {
        field_id: 'text',
        label: 'text',
        value: 'test input',
        page: 0,
        bbox: [250, 50, 400, 70],
      },
    ],
  },
  pipeline_execution: {
    status: 'failure',
    started_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 15000).toISOString(),
    completed_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 30000).toISOString(),
    error_message: 'PermissionError at module m2 (Print Result): Unable to write to output stream: permission denied',
    pipeline_definition_id: 3,  // Pipeline #3 (Minimal - Failure)
    executed_actions: null,
    steps: mockPipeline3FailureExecution,
  },
};

// =============================================================================
// Mock Detail Response for Second Failure Run
// =============================================================================

export const mockFailureRun2Detail: EtoRunDetail = {
  ...mockFailureRun2,
  pdf: {
    ...mockFailureRun2.pdf,
    page_count: 11,
  },
  template_matching: {
    status: 'success',
    started_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 5 * 60 * 60 * 1000 + 5000).toISOString(),
    error_message: null,
    matched_template: createMockTemplate(1, 'Simple Text Processing Template'),
  },
  data_extraction: {
    status: 'success',
    started_at: new Date(Date.now() - 5 * 60 * 60 * 1000 + 5000).toISOString(),
    completed_at: new Date(Date.now() - 5 * 60 * 60 * 1000 + 15000).toISOString(),
    error_message: null,
    // Matches pipeline #1 entry point (e1: input_text) - but extracted null
    extracted_data: {
      input_text: null,
    },
    extracted_fields_with_boxes: [
      {
        field_id: 'input_text',
        label: 'input_text',
        value: null,
        page: 0,
        bbox: [250, 50, 400, 70],
      },
    ],
  },
  pipeline_execution: {
    status: 'failure',
    started_at: new Date(Date.now() - 5 * 60 * 60 * 1000 + 15000).toISOString(),
    completed_at: new Date(Date.now() - 5 * 60 * 60 * 1000 + 20000).toISOString(),
    error_message: 'TypeError at module m1 (Trim): Expected \'str\' but received \'NoneType\' for parameter \'text\'',
    pipeline_definition_id: 1,  // Pipeline #1 (Simple - Failure at first module)
    executed_actions: null,
    steps: mockPipeline1FailureExecution,
  },
};

// =============================================================================
// Mock Detail Response for Third Success Run (Complex Multi-Type Pipeline)
// =============================================================================

export const mockSuccessRun3Detail: EtoRunDetail = {
  ...mockSuccessRun3,
  pdf: {
    ...mockSuccessRun3.pdf,
    page_count: 3,
  },
  template_matching: {
    status: 'success',
    started_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 5.95 * 60 * 60 * 1000).toISOString(),
    error_message: null,
    matched_template: createMockTemplate(4, 'Complex Order Processing Template'),
  },
  data_extraction: {
    status: 'success',
    started_at: new Date(Date.now() - 5.95 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 5.85 * 60 * 60 * 1000).toISOString(),
    error_message: null,
    // Matches pipeline #4 entry points (e1: order_id, e2: quantity, e3: unit_price, e4: is_expedited, e5: order_date)
    extracted_data: {
      order_id: 'ORD-2025-001',
      quantity: 5,
      unit_price: 29.99,
      is_expedited: true,
      order_date: '2025-10-17T10:30:00Z',
    },
    extracted_fields_with_boxes: [
      {
        field_id: 'order_id',
        label: 'order_id',
        value: 'ORD-2025-001',
        page: 0,
        bbox: [100, 50, 300, 70],
      },
      {
        field_id: 'quantity',
        label: 'quantity',
        value: 5,
        page: 0,
        bbox: [100, 100, 200, 120],
      },
      {
        field_id: 'unit_price',
        label: 'unit_price',
        value: 29.99,
        page: 0,
        bbox: [100, 150, 250, 170],
      },
      {
        field_id: 'is_expedited',
        label: 'is_expedited',
        value: true,
        page: 0,
        bbox: [100, 200, 300, 220],
      },
      {
        field_id: 'order_date',
        label: 'order_date',
        value: '2025-10-17T10:30:00Z',
        page: 0,
        bbox: [100, 250, 400, 270],
      },
    ],
  },
  pipeline_execution: {
    status: 'success',
    started_at: new Date(Date.now() - 5.85 * 60 * 60 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 5.8 * 60 * 60 * 1000).toISOString(),
    error_message: null,
    pipeline_definition_id: 4,  // Pipeline #4 (Complex Multi-Type)
    executed_actions: [
      {
        action_module_name: 'Send Email',
        inputs: {
          invoice_id: 'INV-2025-10-17-001',
          order_details: 'ORD-2025-001 | 2025-10-20 | $25.99 | $0.00',
        },
      },
      {
        action_module_name: 'Log Action',
        inputs: {
          message: 'INV-2025-10-17-001',
          success: true,
        },
      },
    ],
    steps: mockPipeline4SuccessExecution,
  },
};

// =============================================================================
// Mock Detail Responses by ID
// =============================================================================

export const mockRunDetailsById: Record<number, EtoRunDetail> = {
  2: mockProcessingRunDetail, // Processing run with PDF ID 3
  3: mockSuccessRunDetail,     // Success run with PDF ID 2 (pipeline #1 success)
  4: mockFailureRunDetail,     // Failure run with PDF ID 4 (pipeline #3 failure)
  7: mockSuccessRun2Detail,    // Second success run with PDF ID 4 (pipeline #2 success)
  8: mockFailureRun2Detail,    // Second failure run with PDF ID 103 (pipeline #1 failure)
  11: mockSuccessRun3Detail,   // Third success run with PDF ID 103 (pipeline #4 success)
};
