/**
 * Mock Pipeline Definitions (API-formatted)
 * Single source of truth for pipeline visualization
 * Used across ETO run detail, template editor, and standalone testing
 *
 * ID Scheme:
 * - Entry points: e1, e2, e3...
 * - Modules: m1, m2, m3...
 * - Input nodes: i1, i2, i3... (global numbering)
 * - Output nodes: o1, o2, o3... (global numbering)
 *
 * Note: Every input pin is connected to exactly one output pin
 * All type constraints are satisfied
 */

import type { PipelineState, VisualState } from '../types';

/**
 * Pipeline #1: Simple Text Processing
 * Linear flow with 3 modules
 * All inputs connected, all types match (str → str → str)
 *
 * Flow:
 * e1 (input_text) → m1 (trim) → m2 (uppercase) → m3 (print)
 */
export const mockPipelineDefinition = {
  id: 1,
  compiled_plan_id: 1,

  // Logical pipeline structure
  pipeline_state: {
    entry_points: [
      {
        id: 'e1',
        label: 'input_text',
        field_reference: 'input_text',
      },
    ],

    modules: [
      // m1: Trim whitespace
      {
        instance_id: 'm1',
        module_id: 'string_trim:1.0.0',
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
      // m2: Convert to uppercase
      {
        instance_id: 'm2',
        module_id: 'string_uppercase:1.0.0',
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
      // m3: Print action
      {
        instance_id: 'm3',
        module_id: 'print_action:1.0.0',
        config: { prefix: 'Result: ' },
        inputs: [
          {
            node_id: 'i3',
            name: 'message',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o3',
            name: 'success',
            type: ['bool'],
          },
        ],
      },
    ],

    connections: [
      // Linear flow: e1 → m1 → m2 → m3
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
        target_handle_id: 'i2',
      },
      {
        source_module_id: 'm2',
        source_handle_id: 'o2',
        target_module_id: 'm3',
        target_handle_id: 'i3',
      },
    ],
  } as PipelineState,

  // Visual layout for graph builder
  visual_state: {
    positions: {
      e1: { x: 100, y: 200 },
      m1: { x: 400, y: 200 },
      m2: { x: 700, y: 200 },
      m3: { x: 1000, y: 200 },
    },
  } as VisualState,
};

/**
 * Pipeline #2: Complex Multi-Branch Processing
 * Large pipeline with 9 modules, multiple branches that merge
 * All inputs connected, all types match
 *
 * Flow:
 * e1 (hawb) → m1 (trim) → m2 (uppercase) ─┐
 * e2 (customer) → m3 (trim) → m4 (uppercase) ─┤→ m5 (concat) ─┐
 * e3 (weight) ───────────────────────────────┘               │
 *                                                             ├→ m8 (concat) → m9 (print)
 * e4 (dimensions) → m6 (trim) ─┐                              │
 * e1 (hawb) ────────────────────┤→ m7 (concat) ──────────────┘
 * e2 (customer) ────────────────┘
 * e3 (weight) ──────────────────────────────────────────────┘
 */
export const mockComplexPipelineDefinition = {
  id: 2,
  compiled_plan_id: 2,

  pipeline_state: {
    entry_points: [
      {
        id: 'e1',
        label: 'hawb',
        field_reference: 'hawb',
      },
      {
        id: 'e2',
        label: 'customer',
        field_reference: 'customer',
      },
      {
        id: 'e3',
        label: 'weight',
        field_reference: 'weight',
      },
      {
        id: 'e4',
        label: 'dimensions',
        field_reference: 'dimensions',
      },
    ],

    modules: [
      // m1: Trim HAWB
      {
        instance_id: 'm1',
        module_id: 'string_trim:1.0.0',
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
      // m2: Uppercase HAWB
      {
        instance_id: 'm2',
        module_id: 'string_uppercase:1.0.0',
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
      // m3: Trim customer
      {
        instance_id: 'm3',
        module_id: 'string_trim:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i3',
            name: 'text',
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
      // m4: Uppercase customer
      {
        instance_id: 'm4',
        module_id: 'string_uppercase:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i4',
            name: 'text',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o4',
            name: 'result',
            type: ['str'],
          },
        ],
      },
      // m5: Concat HAWB + customer + weight
      {
        instance_id: 'm5',
        module_id: 'string_concat:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i5',
            name: 'string1',
            type: ['str'],
          },
          {
            node_id: 'i6',
            name: 'string2',
            type: ['str'],
          },
          {
            node_id: 'i7',
            name: 'separator',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o5',
            name: 'result',
            type: ['str'],
          },
        ],
      },
      // m6: Trim dimensions
      {
        instance_id: 'm6',
        module_id: 'string_trim:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i8',
            name: 'text',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o6',
            name: 'result',
            type: ['str'],
          },
        ],
      },
      // m7: Concat dimensions + hawb + customer
      {
        instance_id: 'm7',
        module_id: 'string_concat:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i9',
            name: 'string1',
            type: ['str'],
          },
          {
            node_id: 'i10',
            name: 'string2',
            type: ['str'],
          },
          {
            node_id: 'i11',
            name: 'separator',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o7',
            name: 'result',
            type: ['str'],
          },
        ],
      },
      // m8: Final concat - merge both branches
      {
        instance_id: 'm8',
        module_id: 'string_concat:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i12',
            name: 'string1',
            type: ['str'],
          },
          {
            node_id: 'i13',
            name: 'string2',
            type: ['str'],
          },
          {
            node_id: 'i14',
            name: 'separator',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o8',
            name: 'result',
            type: ['str'],
          },
        ],
      },
      // m9: Print final result
      {
        instance_id: 'm9',
        module_id: 'print_action:1.0.0',
        config: { prefix: 'Final: ' },
        inputs: [
          {
            node_id: 'i15',
            name: 'message',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o9',
            name: 'success',
            type: ['bool'],
          },
        ],
      },
    ],

    connections: [
      // Branch 1: HAWB processing
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
        target_handle_id: 'i2',
      },

      // Branch 2: Customer processing
      {
        source_module_id: 'e2',
        source_handle_id: 'e2',
        target_module_id: 'm3',
        target_handle_id: 'i3',
      },
      {
        source_module_id: 'm3',
        source_handle_id: 'o3',
        target_module_id: 'm4',
        target_handle_id: 'i4',
      },

      // First merge: HAWB + Customer + Weight
      {
        source_module_id: 'm2',
        source_handle_id: 'o2',
        target_module_id: 'm5',
        target_handle_id: 'i5',
      },
      {
        source_module_id: 'm4',
        source_handle_id: 'o4',
        target_module_id: 'm5',
        target_handle_id: 'i6',
      },
      {
        source_module_id: 'e3',
        source_handle_id: 'e3',
        target_module_id: 'm5',
        target_handle_id: 'i7',
      },

      // Branch 3: Dimensions processing + reuse HAWB/Customer
      {
        source_module_id: 'e4',
        source_handle_id: 'e4',
        target_module_id: 'm6',
        target_handle_id: 'i8',
      },
      {
        source_module_id: 'm6',
        source_handle_id: 'o6',
        target_module_id: 'm7',
        target_handle_id: 'i9',
      },
      {
        source_module_id: 'e1',
        source_handle_id: 'e1',
        target_module_id: 'm7',
        target_handle_id: 'i10',
      },
      {
        source_module_id: 'e2',
        source_handle_id: 'e2',
        target_module_id: 'm7',
        target_handle_id: 'i11',
      },

      // Final merge: Both branches + weight separator
      {
        source_module_id: 'm5',
        source_handle_id: 'o5',
        target_module_id: 'm8',
        target_handle_id: 'i12',
      },
      {
        source_module_id: 'm7',
        source_handle_id: 'o7',
        target_module_id: 'm8',
        target_handle_id: 'i13',
      },
      {
        source_module_id: 'e3',
        source_handle_id: 'e3',
        target_module_id: 'm8',
        target_handle_id: 'i14',
      },

      // Final action
      {
        source_module_id: 'm8',
        source_handle_id: 'o8',
        target_module_id: 'm9',
        target_handle_id: 'i15',
      },
    ],
  } as PipelineState,

  visual_state: {
    positions: {
      // Entry points (left column)
      e1: { x: 100, y: 100 },
      e2: { x: 100, y: 250 },
      e3: { x: 100, y: 400 },
      e4: { x: 100, y: 550 },

      // First processing layer
      m1: { x: 400, y: 100 },
      m3: { x: 400, y: 250 },
      m6: { x: 400, y: 550 },

      // Second processing layer
      m2: { x: 700, y: 100 },
      m4: { x: 700, y: 250 },

      // First merge layer
      m5: { x: 1000, y: 175 },
      m7: { x: 1000, y: 475 },

      // Final merge layer
      m8: { x: 1300, y: 325 },

      // Final action
      m9: { x: 1600, y: 325 },
    },
  } as VisualState,
};

/**
 * Pipeline #3: Minimal Valid Pipeline
 * Simplest possible pipeline with 2 modules
 * All inputs connected, all types match
 *
 * Flow:
 * e1 (text) → m1 (uppercase) → m2 (print)
 */
export const mockSimplePipelineDefinition = {
  id: 3,
  compiled_plan_id: 3,

  pipeline_state: {
    entry_points: [
      {
        id: 'e1',
        label: 'text',
        field_reference: 'text',
      },
    ],

    modules: [
      // m1: Convert to uppercase
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
      // m2: Print result
      {
        instance_id: 'm2',
        module_id: 'print_action:1.0.0',
        config: { prefix: 'Output: ' },
        inputs: [
          {
            node_id: 'i2',
            name: 'message',
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
      // Simple linear flow
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
        target_handle_id: 'i2',
      },
    ],
  } as PipelineState,

  visual_state: {
    positions: {
      e1: { x: 100, y: 150 },
      m1: { x: 400, y: 150 },
      m2: { x: 700, y: 150 },
    },
  } as VisualState,
};
