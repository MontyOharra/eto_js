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

export const mockActiveTemplate: TemplateListItem = {
  id: 1,
  name: 'Standard HAWB Template',
  description: 'Standard template for House Air Waybill documents',
  status: 'active',
  source_pdf_id: 101,
  current_version: createMockVersionSummary(1, 1, 25),
  total_versions: 1,
};

export const mockActiveTemplateWithVersions: TemplateListItem = {
  id: 2,
  name: 'Commercial Invoice Template',
  description: 'Template for commercial invoice processing',
  status: 'active',
  source_pdf_id: 102,
  current_version: createMockVersionSummary(4, 3, 12),
  total_versions: 3,
};

export const mockInactiveTemplate: TemplateListItem = {
  id: 3,
  name: 'Legacy Invoice Template',
  description: 'Old template - no longer in use',
  status: 'inactive',
  source_pdf_id: 103,
  current_version: createMockVersionSummary(5, 1, 8),
  total_versions: 1,
};

export const mockDraftTemplate: TemplateListItem = {
  id: 4,
  name: 'Bill of Lading Template',
  description: 'In progress - not yet activated',
  status: 'draft',
  source_pdf_id: 104,
  current_version: createMockVersionSummary(6, 1, 0),
  total_versions: 1,
};

export const mockActiveTemplate2: TemplateListItem = {
  id: 5,
  name: 'Packing List Template',
  description: 'Template for packing list documents',
  status: 'active',
  source_pdf_id: 105,
  current_version: createMockVersionSummary(7, 2, 18),
  total_versions: 2,
};

export const mockDraftTemplate2: TemplateListItem = {
  id: 6,
  name: 'Customs Declaration',
  description: null,
  status: 'draft',
  source_pdf_id: 106,
  current_version: createMockVersionSummary(8, 1, 0),
  total_versions: 1,
};

// =============================================================================
// Collections
// =============================================================================

export const allMockTemplates: TemplateListItem[] = [
  mockActiveTemplate,
  mockActiveTemplateWithVersions,
  mockInactiveTemplate,
  mockDraftTemplate,
  mockActiveTemplate2,
  mockDraftTemplate2,
];

export const mockTemplatesByStatus: Record<TemplateStatus, TemplateListItem[]> =
  {
    active: [mockActiveTemplate, mockActiveTemplateWithVersions, mockActiveTemplate2],
    inactive: [mockInactiveTemplate],
    draft: [mockDraftTemplate, mockDraftTemplate2],
  };

// =============================================================================
// Template Detail Response
// =============================================================================

export const mockTemplateDetail: TemplateDetail = {
  // Template metadata
  id: 1,
  name: 'Standard HAWB Template',
  description: 'Standard template for House Air Waybill documents',
  source_pdf_id: 101,
  status: 'active',
  current_version_id: 1,

  // Current version details
  current_version: {
    version_id: 1,
    version_num: 1,
    usage_count: 25,
    last_used_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    signature_objects: createMockSignatureObjects(),
    extraction_fields: createMockExtractionFields(),
    pipeline_definition_id: 201,
  },

  // Version history
  total_versions: 1,
};

export const mockTemplateDetailMultiVersion: TemplateDetail = {
  id: 2,
  name: 'Commercial Invoice Template',
  description: 'Template for commercial invoice processing',
  source_pdf_id: 102,
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
  1: mockTemplateDetail,
  2: mockTemplateDetailMultiVersion,
  3: {
    id: 3,
    name: 'Legacy Invoice Template',
    description: 'Old template - no longer in use',
    source_pdf_id: 103,
    status: 'inactive',
    current_version_id: 5,
    current_version: {
      version_id: 5,
      version_num: 1,
      usage_count: 8,
      last_used_at: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
      signature_objects: createMockSignatureObjects(),
      extraction_fields: createMockExtractionFields(),
      pipeline_definition_id: 203,
    },
    total_versions: 1,
  },
  4: {
    id: 4,
    name: 'Bill of Lading Template',
    description: 'In progress - not yet activated',
    source_pdf_id: 104,
    status: 'draft',
    current_version_id: 6,
    current_version: {
      version_id: 6,
      version_num: 1,
      usage_count: 0,
      last_used_at: null,
      signature_objects: createMockSignatureObjects(),
      extraction_fields: createMockExtractionFields(),
      pipeline_definition_id: 204,
    },
    total_versions: 1,
  },
  5: {
    id: 5,
    name: 'Packing List Template',
    description: 'Template for packing list documents',
    source_pdf_id: 105,
    status: 'active',
    current_version_id: 7,
    current_version: {
      version_id: 7,
      version_num: 2,
      usage_count: 18,
      last_used_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
      signature_objects: createMockSignatureObjects(),
      extraction_fields: createMockExtractionFields(),
      pipeline_definition_id: 205,
    },
    total_versions: 2,
  },
  6: {
    id: 6,
    name: 'Customs Declaration',
    description: null,
    source_pdf_id: 106,
    status: 'draft',
    current_version_id: 8,
    current_version: {
      version_id: 8,
      version_num: 1,
      usage_count: 0,
      last_used_at: null,
      signature_objects: createMockSignatureObjects(),
      extraction_fields: createMockExtractionFields(),
      pipeline_definition_id: 206,
    },
    total_versions: 1,
  },
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
  template_id: 2,
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
  id: 7,
  name: 'New Template',
  status: 'draft',
  current_version_id: 9,
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
