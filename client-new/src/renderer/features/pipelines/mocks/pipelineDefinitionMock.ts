/**
 * Mock Pipeline Definition (API-formatted)
 * Single source of truth for pipeline visualization
 * Used across ETO run detail, template editor, and standalone testing
 *
 * ID Scheme:
 * - Entry points: e1, e2, e3...
 * - Modules: m1, m2, m3...
 * - Input nodes: i1, i2, i3... (global numbering)
 * - Output nodes: o1, o2, o3... (global numbering)
 */

import type { PipelineState, VisualState } from '../types';

/**
 * Mock Pipeline Definition #1
 * Simple HAWB processing pipeline with string transformations and email action
 *
 * Flow:
 * e1 (hawb) -> m1 (uppercase) -> m3 (concat) -> m4 (email)
 * e2 (customer) -> m2 (trim) -> m3 (concat)
 * e3 (weight) - not connected
 */
export const mockPipelineDefinition = {
  id: 1,
  compiled_plan_id: 1,

  // Logical pipeline structure
  pipeline_state: {
    entry_points: [
      {
        id: 'e1',
        label: 'hawb',
        field_reference: 'hawb',
      },
      {
        id: 'e2',
        label: 'customer_name',
        field_reference: 'customer_name',
      },
      {
        id: 'e3',
        label: 'weight',
        field_reference: 'weight',
      },
    ],

    modules: [
      // m1: Uppercase transformation
      {
        instance_id: 'm1',
        module_id: 'string_uppercase:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i1',
            name: 'text',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o1',
            name: 'result',
            type: ['str'],
          },
        ],
      },
      // m2: Trim transformation
      {
        instance_id: 'm2',
        module_id: 'string_trim:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i2',
            name: 'text',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o2',
            name: 'result',
            type: ['str'],
          },
        ],
      },
      // m3: Concatenate transformation
      {
        instance_id: 'm3',
        module_id: 'string_concat:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i3',
            name: 'string1',
            type: ['str'],
          },
          {
            node_id: 'i4',
            name: 'string2',
            type: ['str'],
          },
          {
            node_id: 'i5',
            name: 'separator',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o3',
            name: 'result',
            type: ['str'],
          },
        ],
      },
      // m4: Email action
      {
        instance_id: 'm4',
        module_id: 'action_email:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i6',
            name: 'recipient',
            type: ['str'],
          },
          {
            node_id: 'i7',
            name: 'subject',
            type: ['str'],
          },
          {
            node_id: 'i8',
            name: 'body',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o4',
            name: 'success',
            type: ['bool'],
          },
        ],
      },
    ],

    connections: [
      // Entry points to first layer
      {
        source_module_id: 'e1',
        source_handle_id: 'e1',
        target_module_id: 'm1',
        target_handle_id: 'i1',
      },
      {
        source_module_id: 'e2',
        source_handle_id: 'e2',
        target_module_id: 'm2',
        target_handle_id: 'i2',
      },

      // First layer to concat
      {
        source_module_id: 'm1',
        source_handle_id: 'o1',
        target_module_id: 'm3',
        target_handle_id: 'i3',
      },
      {
        source_module_id: 'm2',
        source_handle_id: 'o2',
        target_module_id: 'm3',
        target_handle_id: 'i4',
      },

      // Concat to email
      {
        source_module_id: 'm3',
        source_handle_id: 'o3',
        target_module_id: 'm4',
        target_handle_id: 'i8',
      },
    ],
  } as PipelineState,

  // Visual layout for graph builder
  visual_state: {
    positions: {
      e1: { x: 100, y: 100 },
      e2: { x: 100, y: 250 },
      e3: { x: 100, y: 400 },
      m1: { x: 400, y: 100 },
      m2: { x: 400, y: 250 },
      m3: { x: 700, y: 175 },
      m4: { x: 1000, y: 200 },
    },
  } as VisualState,
};

/**
 * Mock execution data for pipeline #1
 * Used to overlay runtime values in ETO run detail view
 */
export const mockPipelineExecutionData = {
  steps: [
    {
      id: 1,
      step_number: 1,
      module_instance_id: 'm1',
      inputs: {
        text: { value: 'HAWB-2024-12345', type: 'str' },
      },
      outputs: {
        result: { value: 'HAWB-2024-12345', type: 'str' },
      },
      error: null,
    },
    {
      id: 2,
      step_number: 2,
      module_instance_id: 'm2',
      inputs: {
        text: { value: 'Acme Corporation', type: 'str' },
      },
      outputs: {
        result: { value: 'Acme Corporation', type: 'str' },
      },
      error: null,
    },
    {
      id: 3,
      step_number: 3,
      module_instance_id: 'm3',
      inputs: {
        string1: { value: 'HAWB-2024-12345', type: 'str' },
        string2: { value: 'Acme Corporation', type: 'str' },
        separator: { value: ' - ', type: 'str' },
      },
      outputs: {
        result: { value: 'HAWB-2024-12345 - Acme Corporation', type: 'str' },
      },
      error: null,
    },
    {
      id: 4,
      step_number: 4,
      module_instance_id: 'm4',
      inputs: {
        recipient: { value: 'warehouse@acme.com', type: 'str' },
        subject: { value: 'New HAWB Received', type: 'str' },
        body: { value: 'HAWB-2024-12345 - Acme Corporation', type: 'str' },
      },
      outputs: {
        success: { value: true, type: 'bool' },
      },
      error: null,
    },
  ],
  executed_actions: [
    {
      action_module_name: 'Send Email',
      inputs: {
        recipient: 'warehouse@acme.com',
        subject: 'New HAWB Received',
        body: 'HAWB-2024-12345 - Acme Corporation',
      },
    },
  ],
};

/**
 * Failed pipeline execution example
 *
 * Flow:
 * e1 (hawb) -> m1 (validate) [FAILS] -> m2 (email) [NOT EXECUTED]
 */
export const mockFailedPipelineDefinition = {
  id: 2,
  compiled_plan_id: 2,

  pipeline_state: {
    entry_points: [
      {
        id: 'e1',
        label: 'hawb',
        field_reference: 'hawb',
      },
    ],

    modules: [
      // m1: Validate regex
      {
        instance_id: 'm1',
        module_id: 'validate_regex:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i1',
            name: 'text',
            type: ['str'],
          },
          {
            node_id: 'i2',
            name: 'pattern',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o1',
            name: 'result',
            type: ['bool'],
          },
        ],
      },
      // m2: Email action
      {
        instance_id: 'm2',
        module_id: 'action_email:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i3',
            name: 'recipient',
            type: ['str'],
          },
          {
            node_id: 'i4',
            name: 'subject',
            type: ['str'],
          },
          {
            node_id: 'i5',
            name: 'body',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o2',
            name: 'success',
            type: ['bool'],
          },
        ],
      },
    ],

    connections: [
      {
        source_module_id: 'e1',
        source_handle_id: 'e1',
        target_module_id: 'm1',
        target_handle_id: 'i1',
      },
      {
        source_module_id: 'm1',
        source_handle_id: 'o1',
        target_module_id: 'm2',
        target_handle_id: 'i5',
      },
    ],
  } as PipelineState,

  visual_state: {
    positions: {
      e1: { x: 100, y: 100 },
      m1: { x: 400, y: 100 },
      m2: { x: 700, y: 100 },
    },
  } as VisualState,
};

export const mockFailedPipelineExecutionData = {
  steps: [
    {
      id: 1,
      step_number: 1,
      module_instance_id: 'm1',
      inputs: {
        text: { value: 'HAWB-2024-99999', type: 'str' },
        pattern: { value: '^HAWB-2024-[0-5]', type: 'str' },
      },
      outputs: null,
      error: {
        type: 'ValidationError',
        message: 'Input does not match required pattern',
      },
    },
    // m2 never executed due to error
  ],
  executed_actions: [],
};
