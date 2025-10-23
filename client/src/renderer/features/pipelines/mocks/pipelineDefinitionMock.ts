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

/**
 * Pipeline #4: Complex Multi-Type Data Processing
 * Complex pipeline with 12 modules showcasing:
 * - All type variations (str, int, float, bool, datetime)
 * - Different module kinds (transform, action, logic)
 * - Strict one-to-one connections (no output reuse)
 * - Multiple configurations
 *
 * Flow (one-to-one only):
 * e1 (order_id: str) → m1 (validate_order) → m2 (format_order_id) ──┐
 * e2 (quantity: int) ─────────────────────────────────────────────┐  │
 * e3 (unit_price: float) ─────────────────────────────────────┐   │  │
 *                                                              │   │  │
 * e4 (is_expedited: bool) → m3 (get_shipping) → m4 (format) ─┐│   │  │
 *                                                              ││   │  │
 * e5 (order_date: datetime) → m5 (add_days) → m6 (format) ───┤│   │  │
 *                                                              ││   │  │
 *                                      m7 (calc_subtotal) ←───┴┼───┘  │
 *                                                ↓             │       │
 *                                      m8 (calc_total) ←──────┘       │
 *                                                ↓                     │
 *                                      m9 (round) → m10 (invoice) ←───┘
 *                                                        ↓
 *                                                   m11 (notify) → m12 (log)
 */
export const mockComplexTypePipelineDefinition = {
  id: 4,
  compiled_plan_id: 4,

  pipeline_state: {
    entry_points: [
      {
        id: 'e1',
        label: 'order_id',
        field_reference: 'order_id',
      },
      {
        id: 'e2',
        label: 'quantity',
        field_reference: 'quantity',
      },
      {
        id: 'e3',
        label: 'unit_price',
        field_reference: 'unit_price',
      },
      {
        id: 'e4',
        label: 'is_expedited',
        field_reference: 'is_expedited',
      },
      {
        id: 'e5',
        label: 'order_date',
        field_reference: 'order_date',
      },
    ],

    modules: [
      // m1: Validate order ID (transform)
      {
        instance_id: 'm1',
        module_id: 'string_validate:1.0.0',
        config: { pattern: 'ORD-' },
        inputs: [
          {
            node_id: 'i1',
            name: 'order_id',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o1',
            name: 'is_valid',
            type: ['bool'],
          },
        ],
      },
      // m2: Calculate subtotal (transform)
      {
        instance_id: 'm2',
        module_id: 'math_multiply:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i4',
            name: 'quantity',
            type: ['int'],
          },
          {
            node_id: 'i5',
            name: 'unit_price',
            type: ['float'],
          },
        ],
        outputs: [
          {
            node_id: 'o3',
            name: 'subtotal',
            type: ['float'],
          },
        ],
      },
      // m3: Get shipping cost based on expedited flag (logic)
      {
        instance_id: 'm3',
        module_id: 'logic_conditional:1.0.0',
        config: { true_value: 25.99, false_value: 5.99 },
        inputs: [
          {
            node_id: 'i6',
            name: 'condition',
            type: ['bool'],
          },
        ],
        outputs: [
          {
            node_id: 'o4',
            name: 'shipping_cost',
            type: ['float'],
          },
        ],
      },
      // m4: Format shipping as currency string (transform)
      {
        instance_id: 'm4',
        module_id: 'format_currency:1.0.0',
        config: { currency_symbol: '$', decimal_places: 2 },
        inputs: [
          {
            node_id: 'i7',
            name: 'amount',
            type: ['float'],
          },
        ],
        outputs: [
          {
            node_id: 'o5',
            name: 'formatted',
            type: ['str'],
          },
        ],
      },
      // m5: Add delivery days to order date (transform)
      {
        instance_id: 'm5',
        module_id: 'datetime_add_days:1.0.0',
        config: { days: 3 },
        inputs: [
          {
            node_id: 'i8',
            name: 'date',
            type: ['datetime'],
          },
        ],
        outputs: [
          {
            node_id: 'o6',
            name: 'delivery_date',
            type: ['datetime'],
          },
        ],
      },
      // m6: Check if delivery falls on weekend (logic)
      {
        instance_id: 'm6',
        module_id: 'datetime_is_weekend:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i9',
            name: 'date',
            type: ['datetime'],
          },
        ],
        outputs: [
          {
            node_id: 'o7',
            name: 'is_weekend',
            type: ['bool'],
          },
        ],
      },
      // m7: Parse delivery date to string (transform)
      {
        instance_id: 'm7',
        module_id: 'datetime_format:1.0.0',
        config: { format_string: '%Y-%m-%d' },
        inputs: [
          {
            node_id: 'i10',
            name: 'date',
            type: ['datetime'],
          },
        ],
        outputs: [
          {
            node_id: 'o8',
            name: 'date_string',
            type: ['str'],
          },
        ],
      },
      // m8: Apply weekend discount if applicable (logic)
      {
        instance_id: 'm8',
        module_id: 'logic_discount_calculator:1.0.0',
        config: { discount_percentage: 10 },
        inputs: [
          {
            node_id: 'i11',
            name: 'is_weekend',
            type: ['bool'],
          },
          {
            node_id: 'i12',
            name: 'subtotal',
            type: ['float'],
          },
        ],
        outputs: [
          {
            node_id: 'o9',
            name: 'discount_amount',
            type: ['float'],
          },
        ],
      },
      // m9: Format discount amount (transform)
      {
        instance_id: 'm9',
        module_id: 'format_currency:1.0.0',
        config: { currency_symbol: '$', decimal_places: 2 },
        inputs: [
          {
            node_id: 'i13',
            name: 'amount',
            type: ['float'],
          },
        ],
        outputs: [
          {
            node_id: 'o10',
            name: 'formatted',
            type: ['str'],
          },
        ],
      },
      // m10: Concatenate order details (transform)
      {
        instance_id: 'm10',
        module_id: 'string_concat_multi:1.0.0',
        config: { separator: ' | ' },
        inputs: [
          {
            node_id: 'i14',
            name: 'order_id',
            type: ['str'],
          },
          {
            node_id: 'i15',
            name: 'delivery_date',
            type: ['str'],
          },
          {
            node_id: 'i16',
            name: 'shipping',
            type: ['str'],
          },
          {
            node_id: 'i17',
            name: 'discount',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o11',
            name: 'details',
            type: ['str'],
          },
        ],
      },
      // m11: Calculate final total (transform)
      {
        instance_id: 'm11',
        module_id: 'math_calculate_total:1.0.0',
        config: {},
        inputs: [
          {
            node_id: 'i18',
            name: 'subtotal',
            type: ['float'],
          },
          {
            node_id: 'i19',
            name: 'shipping',
            type: ['float'],
          },
          {
            node_id: 'i20',
            name: 'discount',
            type: ['float'],
          },
        ],
        outputs: [
          {
            node_id: 'o12',
            name: 'total',
            type: ['float'],
          },
        ],
      },
      // m12: Round to cents (transform)
      {
        instance_id: 'm12',
        module_id: 'math_round:1.0.0',
        config: { decimal_places: 2 },
        inputs: [
          {
            node_id: 'i21',
            name: 'value',
            type: ['float'],
          },
        ],
        outputs: [
          {
            node_id: 'o13',
            name: 'rounded',
            type: ['float'],
          },
        ],
      },
      // m13: Create invoice document (transform)
      {
        instance_id: 'm13',
        module_id: 'invoice_generator:1.0.0',
        config: { template: 'standard', include_logo: true },
        inputs: [
          {
            node_id: 'i22',
            name: 'total',
            type: ['float'],
          },
          {
            node_id: 'i23',
            name: 'details',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o14',
            name: 'invoice_id',
            type: ['str'],
          },
          {
            node_id: 'o15',
            name: 'invoice_total',
            type: ['float'],
          },
        ],
      },
      // m14: Send notification (action)
      {
        instance_id: 'm14',
        module_id: 'action_send_email:1.0.0',
        config: { recipient: 'orders@example.com', subject: 'New Order Invoice' },
        inputs: [
          {
            node_id: 'i24',
            name: 'invoice_id',
            type: ['str'],
          },
          {
            node_id: 'i25',
            name: 'order_details',
            type: ['str'],
          },
        ],
        outputs: [
          {
            node_id: 'o16',
            name: 'email_sent',
            type: ['bool'],
          },
        ],
      },
      // m15: Log final action (action)
      {
        instance_id: 'm15',
        module_id: 'action_log:1.0.0',
        config: { log_level: 'INFO', include_timestamp: true },
        inputs: [
          {
            node_id: 'i26',
            name: 'message',
            type: ['str'],
          },
          {
            node_id: 'i27',
            name: 'success',
            type: ['bool'],
          },
        ],
        outputs: [
          {
            node_id: 'o17',
            name: 'logged',
            type: ['bool'],
          },
        ],
      },
    ],

    connections: [
      // Entry point connections
      { source_module_id: 'e1', source_handle_id: 'e1', target_module_id: 'm1', target_handle_id: 'i1' },
      { source_module_id: 'e2', source_handle_id: 'e2', target_module_id: 'm1', target_handle_id: 'i2' },
      { source_module_id: 'e3', source_handle_id: 'e3', target_module_id: 'm1', target_handle_id: 'i3' },
      { source_module_id: 'e4', source_handle_id: 'e4', target_module_id: 'm3', target_handle_id: 'i6' },
      { source_module_id: 'e5', source_handle_id: 'e5', target_module_id: 'm5', target_handle_id: 'i8' },

      // Validation to subtotal calculation
      { source_module_id: 'e2', source_handle_id: 'e2', target_module_id: 'm2', target_handle_id: 'i4' },
      { source_module_id: 'e3', source_handle_id: 'e3', target_module_id: 'm2', target_handle_id: 'i5' },

      // Shipping cost formatting
      { source_module_id: 'm3', source_handle_id: 'o4', target_module_id: 'm4', target_handle_id: 'i7' },

      // Date processing branch
      { source_module_id: 'm5', source_handle_id: 'o6', target_module_id: 'm6', target_handle_id: 'i9' },
      { source_module_id: 'm5', source_handle_id: 'o6', target_module_id: 'm7', target_handle_id: 'i10' },

      // Weekend discount logic
      { source_module_id: 'm6', source_handle_id: 'o7', target_module_id: 'm8', target_handle_id: 'i11' },
      { source_module_id: 'm2', source_handle_id: 'o3', target_module_id: 'm8', target_handle_id: 'i12' },

      // Format discount
      { source_module_id: 'm8', source_handle_id: 'o9', target_module_id: 'm9', target_handle_id: 'i13' },

      // Concatenate details
      { source_module_id: 'm1', source_handle_id: 'o2', target_module_id: 'm10', target_handle_id: 'i14' },
      { source_module_id: 'm7', source_handle_id: 'o8', target_module_id: 'm10', target_handle_id: 'i15' },
      { source_module_id: 'm4', source_handle_id: 'o5', target_module_id: 'm10', target_handle_id: 'i16' },
      { source_module_id: 'm9', source_handle_id: 'o10', target_module_id: 'm10', target_handle_id: 'i17' },

      // Calculate total
      { source_module_id: 'm2', source_handle_id: 'o3', target_module_id: 'm11', target_handle_id: 'i18' },
      { source_module_id: 'm3', source_handle_id: 'o4', target_module_id: 'm11', target_handle_id: 'i19' },
      { source_module_id: 'm8', source_handle_id: 'o9', target_module_id: 'm11', target_handle_id: 'i20' },

      // Round and create invoice
      { source_module_id: 'm11', source_handle_id: 'o12', target_module_id: 'm12', target_handle_id: 'i21' },
      { source_module_id: 'm12', source_handle_id: 'o13', target_module_id: 'm13', target_handle_id: 'i22' },
      { source_module_id: 'm10', source_handle_id: 'o11', target_module_id: 'm13', target_handle_id: 'i23' },

      // Send notification
      { source_module_id: 'm13', source_handle_id: 'o14', target_module_id: 'm14', target_handle_id: 'i24' },
      { source_module_id: 'm10', source_handle_id: 'o11', target_module_id: 'm14', target_handle_id: 'i25' },

      // Log action
      { source_module_id: 'm13', source_handle_id: 'o14', target_module_id: 'm15', target_handle_id: 'i26' },
      { source_module_id: 'm14', source_handle_id: 'o16', target_module_id: 'm15', target_handle_id: 'i27' },
    ],
  } as PipelineState,

  visual_state: {
    positions: {
      // Entry points (left column)
      e1: { x: 100, y: 100 },
      e2: { x: 100, y: 200 },
      e3: { x: 100, y: 300 },
      e4: { x: 100, y: 450 },
      e5: { x: 100, y: 600 },

      // First layer: validation & parallel processing
      m1: { x: 400, y: 200 },
      m3: { x: 400, y: 450 },
      m5: { x: 400, y: 600 },

      // Second layer
      m2: { x: 700, y: 250 },
      m4: { x: 700, y: 450 },
      m6: { x: 700, y: 600 },
      m7: { x: 700, y: 700 },

      // Third layer: logic and formatting
      m8: { x: 1000, y: 500 },
      m9: { x: 1300, y: 500 },

      // Fourth layer: concatenation
      m10: { x: 1300, y: 600 },

      // Fifth layer: totals
      m11: { x: 1300, y: 350 },

      // Sixth layer: rounding & invoice
      m12: { x: 1600, y: 350 },
      m13: { x: 1900, y: 475 },

      // Seventh layer: notification & logging
      m14: { x: 2200, y: 475 },
      m15: { x: 2500, y: 475 },
    },
  } as VisualState,
};
