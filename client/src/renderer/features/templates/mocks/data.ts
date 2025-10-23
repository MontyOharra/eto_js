/**
 * Mock Template Data
 * Provides realistic mock data for all template endpoints
 */

import {
  TemplateStatus,
  TemplateListItem,
  TemplateDetail,
  TemplateVersionListItem,
  TemplateVersionDetail,
  SignatureObject,
  ExtractionField,
  TemplateVersionSummary,
  TemplateVersion,
  PipelineState,
  VisualState,
} from '../types';
import {
  GetTemplatesResponse,
  GetTemplateDetailResponse,
  PostTemplateCreateResponse,
  GetTemplateVersionsResponse,
  GetTemplateVersionDetailResponse,
  PostTemplateSimulateResponse,
} from '../api/types';

// =============================================================================
// Helper Functions
// =============================================================================

const createMockSignatureObjects = (): SignatureObject[] => [
  {
    object_type: 'text_word',
    page: 0,
    bbox: [100, 50, 200, 70],
    text: 'HAWB',
    fontname: 'Arial-Bold',
    fontsize: 14,
  },
  {
    object_type: 'graphic_rect',
    page: 0,
    bbox: [95, 45, 205, 75],
    linewidth: 2,
  },
  {
    object_type: 'text_line',
    page: 0,
    bbox: [100, 100, 400, 120],
  },
];

const createMockExtractionFields = (): ExtractionField[] => [
  {
    field_id: 'hawb',
    label: 'hawb',
    description: 'House Air Waybill Number',
    page: 0,
    bbox: [250, 50, 400, 70],
    required: true,
    validation_regex: '^[A-Z0-9]{8,12}$',
  },
  {
    field_id: 'customer_name',
    label: 'customer_name',
    description: 'Customer Name',
    page: 0,
    bbox: [250, 100, 500, 120],
    required: true,
    validation_regex: null,
  },
  {
    field_id: 'weight',
    label: 'weight',
    description: 'Package Weight (kg)',
    page: 0,
    bbox: [250, 150, 350, 170],
    required: false,
    validation_regex: '^\\d+(\\.\\d{1,2})?$',
  },
];

const createMockPipelineState = (): PipelineState => ({
  entry_points: [
    {
      id: 'ep_hawb',
      label: 'HAWB',
      field_reference: 'hawb',
    },
    {
      id: 'ep_customer',
      label: 'Customer Name',
      field_reference: 'customer_name',
    },
  ],
  modules: [
    {
      instance_id: 'mod_1',
      module_id: 'string_uppercase',
      config: {},
      inputs: [
        {
          node_id: 'mod_1_in',
          name: 'input',
          type: ['string'],
        },
      ],
      outputs: [
        {
          node_id: 'mod_1_out',
          name: 'output',
          type: ['string'],
        },
      ],
    },
  ],
  connections: [
    {
      from_node_id: 'ep_hawb',
      to_node_id: 'mod_1_in',
    },
  ],
});

const createMockVisualState = (): VisualState => ({
  positions: {
    ep_hawb: { x: 100, y: 100 },
    ep_customer: { x: 100, y: 200 },
    mod_1: { x: 400, y: 100 },
  },
});

const createMockVersionSummary = (
  versionId: number,
  versionNum: number,
  usageCount: number
): TemplateVersionSummary => ({
  version_id: versionId,
  version_num: versionNum,
  usage_count: usageCount,
});

// =============================================================================
// Mock Templates - List Items
// =============================================================================

export const mockActiveTemplateWithVersions: TemplateListItem = {
  id: 1,
  name: 'Commercial Invoice Template',
  description: 'Template for commercial invoice processing',
  status: 'active',
  source_pdf_id: 2, // Points to 2.pdf
  current_version: createMockVersionSummary(4, 3, 12),
  total_versions: 3,
};

// =============================================================================
// Collections
// =============================================================================

export const allMockTemplates: TemplateListItem[] = [
  mockActiveTemplateWithVersions,
];

export const mockTemplatesByStatus: Record<TemplateStatus, TemplateListItem[]> =
  {
    active: [mockActiveTemplateWithVersions],
    inactive: [],
  };

// =============================================================================
// Template Detail Response
// =============================================================================

export const mockTemplateDetailMultiVersion: TemplateDetail = {
  id: 1,
  name: 'Commercial Invoice Template',
  description: 'Template for commercial invoice processing',
  source_pdf_id: 2, // Points to 2.pdf
  status: 'active',
  current_version_id: 4,

  current_version: {
    version_id: 4,
    version_num: 3,
    usage_count: 12,
    last_used_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    signature_objects: createMockSignatureObjects(),
    extraction_fields: createMockExtractionFields(),
    pipeline_definition_id: 202,
  },

  total_versions: 3,
};

// Map of template ID to detail
export const mockTemplateDetailsById: Record<number, TemplateDetail> = {
  1: mockTemplateDetailMultiVersion,
};

// =============================================================================
// Template Versions
// =============================================================================

export const mockTemplateVersions: TemplateVersionListItem[] = [
  {
    version_id: 4,
    version_num: 3,
    usage_count: 12,
    last_used_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    is_current: true,
  },
  {
    version_id: 3,
    version_num: 2,
    usage_count: 8,
    last_used_at: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
    is_current: false,
  },
  {
    version_id: 2,
    version_num: 1,
    usage_count: 5,
    last_used_at: new Date(Date.now() - 120 * 24 * 60 * 60 * 1000).toISOString(),
    is_current: false,
  },
];

export const mockTemplateVersionDetail: TemplateVersionDetail = {
  version_id: 4,
  template_id: 1,
  version_num: 3,
  usage_count: 12,
  last_used_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  is_current: true,
  signature_objects: createMockSignatureObjects(),
  extraction_fields: createMockExtractionFields(),
  pipeline_definition_id: 202,
};

// =============================================================================
// Create/Update Responses
// =============================================================================

export const mockCreateResponse: PostTemplateCreateResponse = {
  id: 2,
  name: 'New Template',
  status: 'inactive',
  current_version_id: 10,
  current_version_num: 1,
  pipeline_definition_id: 207,
};

// =============================================================================
// Simulation Response
// =============================================================================

export const mockSimulateResponse: PostTemplateSimulateResponse = {
  template_matching: {
    status: 'success',
    message: 'Simulation mode - template matching skipped',
  },
  data_extraction: {
    status: 'success',
    extracted_data: {
      hawb: 'ABC12345',
      customer_name: 'Acme Corporation',
      weight: '25.5',
    },
    error_message: null,
    validation_results: [
      {
        field_label: 'hawb',
        required: true,
        has_value: true,
        regex_valid: true,
        error: null,
      },
      {
        field_label: 'customer_name',
        required: true,
        has_value: true,
        regex_valid: null,
        error: null,
      },
      {
        field_label: 'weight',
        required: false,
        has_value: true,
        regex_valid: true,
        error: null,
      },
    ],
  },
  pipeline_execution: {
    status: 'success',
    error_message: null,
    steps: [
      {
        step_number: 1,
        module_instance_id: 'mod_1',
        module_name: 'String Uppercase',
        inputs: {
          input: {
            value: 'ABC12345',
            type: 'string',
          },
        },
        outputs: {
          output: {
            value: 'ABC12345',
            type: 'string',
          },
        },
        error: null,
      },
    ],
    simulated_actions: [
      {
        action_module_name: 'Send Email',
        inputs: {
          to: 'warehouse@example.com',
          subject: 'New HAWB: ABC12345',
          body: 'HAWB ABC12345 has been processed for Acme Corporation',
        },
        simulation_note: 'Action not executed - simulation mode',
      },
    ],
  },
};

export const mockSimulateFailureResponse: PostTemplateSimulateResponse = {
  template_matching: {
    status: 'success',
    message: 'Simulation mode - template matching skipped',
  },
  data_extraction: {
    status: 'failure',
    extracted_data: null,
    error_message: 'Required field "hawb" is empty',
    validation_results: [
      {
        field_label: 'hawb',
        required: true,
        has_value: false,
        regex_valid: null,
        error: 'Required field is empty',
      },
      {
        field_label: 'customer_name',
        required: true,
        has_value: true,
        regex_valid: null,
        error: null,
      },
      {
        field_label: 'weight',
        required: false,
        has_value: false,
        regex_valid: null,
        error: null,
      },
    ],
  },
  pipeline_execution: {
    status: 'success',
    error_message: null,
    steps: [],
    simulated_actions: [],
  },
};
