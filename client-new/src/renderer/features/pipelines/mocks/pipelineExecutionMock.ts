/**
 * Mock Pipeline Execution Data
 * Execution steps for each pipeline definition
 * Uses updated schema with node_id as key
 */

import type { EtoPipelineExecutionStep } from '../../eto/types';

/**
 * Execution #1: Pipeline #1 (Simple) - SUCCESS
 * All 3 modules execute successfully
 *
 * Flow:
 * e1 ("  Hello World  ") → m1 (trim) → m2 (uppercase) → m3 (print)
 */
export const mockPipeline1SuccessExecution: EtoPipelineExecutionStep[] = [
  // Step 1: m1 (trim)
  {
    id: 1,
    step_number: 1,
    module_instance_id: 'm1',
    inputs: {
      i1: {
        name: 'text',
        value: '  Hello World  ',
        type: 'str',
      },
    },
    outputs: {
      o1: {
        name: 'result',
        value: 'Hello World',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 2: m2 (uppercase)
  {
    id: 2,
    step_number: 2,
    module_instance_id: 'm2',
    inputs: {
      i2: {
        name: 'text',
        value: 'Hello World',
        type: 'str',
      },
    },
    outputs: {
      o2: {
        name: 'result',
        value: 'HELLO WORLD',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 3: m3 (print)
  {
    id: 3,
    step_number: 3,
    module_instance_id: 'm3',
    inputs: {
      i3: {
        name: 'message',
        value: 'HELLO WORLD',
        type: 'str',
      },
    },
    outputs: {
      o3: {
        name: 'success',
        value: true,
        type: 'bool',
      },
    },
    error: null,
  },
];

/**
 * Execution #2: Pipeline #2 (Complex) - SUCCESS
 * All 9 modules execute successfully
 * Demonstrates parallel execution and merge patterns
 *
 * Execution order (determined by Dask DAG):
 * 1. m1, m3, m6 (parallel - no dependencies on each other)
 * 2. m2, m4 (parallel - depend on m1, m3 respectively)
 * 3. m5, m7 (parallel - merge points)
 * 4. m8 (depends on both m5 and m7)
 * 5. m9 (final action)
 */
export const mockPipeline2SuccessExecution: EtoPipelineExecutionStep[] = [
  // Step 1: m1 (trim HAWB)
  {
    id: 1,
    step_number: 1,
    module_instance_id: 'm1',
    inputs: {
      i1: {
        name: 'text',
        value: '  HAWB-2024-12345  ',
        type: 'str',
      },
    },
    outputs: {
      o1: {
        name: 'result',
        value: 'HAWB-2024-12345',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 2: m3 (trim customer) - parallel with m1
  {
    id: 2,
    step_number: 2,
    module_instance_id: 'm3',
    inputs: {
      i3: {
        name: 'text',
        value: '  Acme Corporation  ',
        type: 'str',
      },
    },
    outputs: {
      o3: {
        name: 'result',
        value: 'Acme Corporation',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 3: m6 (trim dimensions) - parallel with m1, m3
  {
    id: 3,
    step_number: 3,
    module_instance_id: 'm6',
    inputs: {
      i8: {
        name: 'text',
        value: '  48x40x36  ',
        type: 'str',
      },
    },
    outputs: {
      o6: {
        name: 'result',
        value: '48x40x36',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 4: m2 (uppercase HAWB)
  {
    id: 4,
    step_number: 4,
    module_instance_id: 'm2',
    inputs: {
      i2: {
        name: 'text',
        value: 'HAWB-2024-12345',
        type: 'str',
      },
    },
    outputs: {
      o2: {
        name: 'result',
        value: 'HAWB-2024-12345', // Already uppercase
        type: 'str',
      },
    },
    error: null,
  },

  // Step 5: m4 (uppercase customer)
  {
    id: 5,
    step_number: 5,
    module_instance_id: 'm4',
    inputs: {
      i4: {
        name: 'text',
        value: 'Acme Corporation',
        type: 'str',
      },
    },
    outputs: {
      o4: {
        name: 'result',
        value: 'ACME CORPORATION',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 6: m5 (concat HAWB + customer + weight)
  {
    id: 6,
    step_number: 6,
    module_instance_id: 'm5',
    inputs: {
      i5: {
        name: 'string1',
        value: 'HAWB-2024-12345',
        type: 'str',
      },
      i6: {
        name: 'string2',
        value: 'ACME CORPORATION',
        type: 'str',
      },
      i7: {
        name: 'separator',
        value: '250.5',
        type: 'str',
      },
    },
    outputs: {
      o5: {
        name: 'result',
        value: 'HAWB-2024-12345250.5ACME CORPORATION',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 7: m7 (concat dimensions + hawb + customer)
  {
    id: 7,
    step_number: 7,
    module_instance_id: 'm7',
    inputs: {
      i9: {
        name: 'string1',
        value: '48x40x36',
        type: 'str',
      },
      i10: {
        name: 'string2',
        value: '  HAWB-2024-12345  ',
        type: 'str',
      },
      i11: {
        name: 'separator',
        value: '  Acme Corporation  ',
        type: 'str',
      },
    },
    outputs: {
      o7: {
        name: 'result',
        value: '48x40x36  Acme Corporation    HAWB-2024-12345  ',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 8: m8 (final concat - merge both branches)
  {
    id: 8,
    step_number: 8,
    module_instance_id: 'm8',
    inputs: {
      i12: {
        name: 'string1',
        value: 'HAWB-2024-12345250.5ACME CORPORATION',
        type: 'str',
      },
      i13: {
        name: 'string2',
        value: '48x40x36  Acme Corporation    HAWB-2024-12345  ',
        type: 'str',
      },
      i14: {
        name: 'separator',
        value: '250.5',
        type: 'str',
      },
    },
    outputs: {
      o8: {
        name: 'result',
        value: 'HAWB-2024-12345250.5ACME CORPORATION250.548x40x36  Acme Corporation    HAWB-2024-12345  ',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 9: m9 (print final result)
  {
    id: 9,
    step_number: 9,
    module_instance_id: 'm9',
    inputs: {
      i15: {
        name: 'message',
        value: 'HAWB-2024-12345250.5ACME CORPORATION250.548x40x36  Acme Corporation    HAWB-2024-12345  ',
        type: 'str',
      },
    },
    outputs: {
      o9: {
        name: 'success',
        value: true,
        type: 'bool',
      },
    },
    error: null,
  },
];

/**
 * Execution #3: Pipeline #3 (Minimal) - FAILURE
 * Fails at step 2 (m2 - print)
 * Demonstrates error recording with inputs but no outputs
 *
 * Flow:
 * e1 ("test") → m1 (uppercase) → m2 (print) [FAILS]
 */
export const mockPipeline3FailureExecution: EtoPipelineExecutionStep[] = [
  // Step 1: m1 (uppercase) - succeeds
  {
    id: 1,
    step_number: 1,
    module_instance_id: 'm1',
    inputs: {
      i1: {
        name: 'text',
        value: 'test input',
        type: 'str',
      },
    },
    outputs: {
      o1: {
        name: 'result',
        value: 'TEST INPUT',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 2: m2 (print) - FAILS
  {
    id: 2,
    step_number: 2,
    module_instance_id: 'm2',
    inputs: {
      i2: {
        name: 'message',
        value: 'TEST INPUT',
        type: 'str',
      },
    },
    outputs: null, // No outputs because module failed
    error: {
      type: 'PermissionError',
      message: 'Unable to write to output stream: permission denied',
      details: {
        stream: 'stdout',
        errno: 13,
      },
    },
  },
  // No step 3 - execution stopped after m2 failed
];

/**
 * Execution #4: Pipeline #1 (Simple) - FAILURE
 * Alternative failure case - fails at first module
 *
 * Flow:
 * e1 (null) → m1 (trim) [FAILS]
 */
export const mockPipeline1FailureExecution: EtoPipelineExecutionStep[] = [
  // Step 1: m1 (trim) - FAILS due to null input
  {
    id: 1,
    step_number: 1,
    module_instance_id: 'm1',
    inputs: {
      i1: {
        name: 'text',
        value: null,
        type: 'NoneType',
      },
    },
    outputs: null, // No outputs because module failed
    error: {
      type: 'TypeError',
      message: "Expected 'str' but received 'NoneType' for parameter 'text'",
      details: {
        parameter: 'text',
        expected_type: 'str',
        received_type: 'NoneType',
        received_value: null,
      },
    },
  },
  // No further steps - execution stopped after m1 failed
];

/**
 * Execution #5: Pipeline #2 (Complex) - FAILURE
 * Fails at merge point (m5)
 * Shows partial execution of parallel branches
 *
 * Flow:
 * e1 → m1 → m2 ✓
 * e2 → m3 → m4 ✓
 * e3 (invalid) → m5 [FAILS at concat due to type mismatch]
 */
export const mockPipeline2FailureExecution: EtoPipelineExecutionStep[] = [
  // Steps 1-5 same as success case
  {
    id: 1,
    step_number: 1,
    module_instance_id: 'm1',
    inputs: {
      i1: {
        name: 'text',
        value: '  HAWB-2024-99999  ',
        type: 'str',
      },
    },
    outputs: {
      o1: {
        name: 'result',
        value: 'HAWB-2024-99999',
        type: 'str',
      },
    },
    error: null,
  },
  {
    id: 2,
    step_number: 2,
    module_instance_id: 'm3',
    inputs: {
      i3: {
        name: 'text',
        value: '  Test Company  ',
        type: 'str',
      },
    },
    outputs: {
      o3: {
        name: 'result',
        value: 'Test Company',
        type: 'str',
      },
    },
    error: null,
  },
  {
    id: 3,
    step_number: 3,
    module_instance_id: 'm6',
    inputs: {
      i8: {
        name: 'text',
        value: '  24x20x18  ',
        type: 'str',
      },
    },
    outputs: {
      o6: {
        name: 'result',
        value: '24x20x18',
        type: 'str',
      },
    },
    error: null,
  },
  {
    id: 4,
    step_number: 4,
    module_instance_id: 'm2',
    inputs: {
      i2: {
        name: 'text',
        value: 'HAWB-2024-99999',
        type: 'str',
      },
    },
    outputs: {
      o2: {
        name: 'result',
        value: 'HAWB-2024-99999',
        type: 'str',
      },
    },
    error: null,
  },
  {
    id: 5,
    step_number: 5,
    module_instance_id: 'm4',
    inputs: {
      i4: {
        name: 'text',
        value: 'Test Company',
        type: 'str',
      },
    },
    outputs: {
      o4: {
        name: 'result',
        value: 'TEST COMPANY',
        type: 'str',
      },
    },
    error: null,
  },

  // Step 6: m5 - FAILS due to invalid weight value (not a string)
  {
    id: 6,
    step_number: 6,
    module_instance_id: 'm5',
    inputs: {
      i5: {
        name: 'string1',
        value: 'HAWB-2024-99999',
        type: 'str',
      },
      i6: {
        name: 'string2',
        value: 'TEST COMPANY',
        type: 'str',
      },
      i7: {
        name: 'separator',
        value: 123.45, // ERROR: weight came through as number instead of string
        type: 'float',
      },
    },
    outputs: null,
    error: {
      type: 'ValidationError',
      message: "Type constraint violation: expected 'str' for parameter 'separator' but received 'float'",
      details: {
        parameter: 'separator',
        node_id: 'i7',
        expected_types: ['str'],
        received_type: 'float',
        received_value: 123.45,
      },
    },
  },
  // No further steps - m7, m8, m9 never executed
];
