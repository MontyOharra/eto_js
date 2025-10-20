/**
 * Plain Mock Data for Executed Pipeline Visualization
 * Simple test data (not API-formatted)
 */

export const mockExecutedPipelineData = {
  // Entry points from extraction
  entryPoints: [
    {
      id: 'entry_hawb',
      label: 'hawb',
      value: 'HAWB-2024-12345',
      position: { x: 100, y: 100 },
    },
    {
      id: 'entry_customer',
      label: 'customer_name',
      value: 'Acme Corporation',
      position: { x: 100, y: 250 },
    },
    {
      id: 'entry_weight',
      label: 'weight',
      value: '150.5',
      position: { x: 100, y: 400 },
    },
  ],

  // Transformation modules that were executed
  modules: [
    {
      id: 'mod_uppercase',
      name: 'Uppercase Text',
      moduleRef: 'string_uppercase:1.0.0',
      color: '#3B82F6',
      position: { x: 400, y: 100 },
      executed: true,
      inputs: {
        text: { value: 'HAWB-2024-12345', type: 'str' },
      },
      outputs: {
        result: { value: 'HAWB-2024-12345', type: 'str' }, // Already uppercase
      },
    },
    {
      id: 'mod_trim',
      name: 'Trim Text',
      moduleRef: 'string_trim:1.0.0',
      color: '#3B82F6',
      position: { x: 400, y: 250 },
      executed: true,
      inputs: {
        text: { value: 'Acme Corporation', type: 'str' },
      },
      outputs: {
        result: { value: 'Acme Corporation', type: 'str' },
      },
    },
    {
      id: 'mod_concat',
      name: 'Concatenate Strings',
      moduleRef: 'string_concat:1.0.0',
      color: '#3B82F6',
      position: { x: 700, y: 175 },
      executed: true,
      inputs: {
        string1: { value: 'HAWB-2024-12345', type: 'str' },
        string2: { value: 'Acme Corporation', type: 'str' },
        separator: { value: ' - ', type: 'str' },
      },
      outputs: {
        result: { value: 'HAWB-2024-12345 - Acme Corporation', type: 'str' },
      },
    },
    {
      id: 'mod_email',
      name: 'Send Email',
      moduleRef: 'action_email:1.0.0',
      color: '#10B981', // Green for actions
      position: { x: 1000, y: 200 },
      executed: true,
      inputs: {
        recipient: { value: 'warehouse@acme.com', type: 'str' },
        subject: { value: 'New HAWB Received', type: 'str' },
        body: { value: 'HAWB-2024-12345 - Acme Corporation', type: 'str' },
      },
      outputs: {
        success: { value: true, type: 'bool' },
      },
    },
  ],

  // Connections between nodes
  connections: [
    { from: 'entry_hawb', to: 'mod_uppercase', fromPin: 'entry_hawb', toPin: 'text' },
    { from: 'entry_customer', to: 'mod_trim', fromPin: 'entry_customer', toPin: 'text' },
    { from: 'mod_uppercase', to: 'mod_concat', fromPin: 'result', toPin: 'string1' },
    { from: 'mod_trim', to: 'mod_concat', fromPin: 'result', toPin: 'string2' },
    { from: 'mod_concat', to: 'mod_email', fromPin: 'result', toPin: 'body' },
  ],
};

// Failed execution example
export const mockFailedPipelineData = {
  entryPoints: [
    {
      id: 'entry_hawb',
      label: 'hawb',
      value: 'HAWB-2024-99999',
      position: { x: 100, y: 100 },
    },
  ],

  modules: [
    {
      id: 'mod_validate',
      name: 'Validate Format',
      moduleRef: 'validate_regex:1.0.0',
      color: '#F59E0B',
      position: { x: 400, y: 100 },
      executed: true,
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
    {
      id: 'mod_email',
      name: 'Send Email',
      moduleRef: 'action_email:1.0.0',
      color: '#6B7280', // Gray - not executed
      position: { x: 700, y: 100 },
      executed: false,
      inputs: null,
      outputs: null,
    },
  ],

  connections: [
    { from: 'entry_hawb', to: 'mod_validate', fromPin: 'entry_hawb', toPin: 'text' },
    { from: 'mod_validate', to: 'mod_email', fromPin: 'result', toPin: 'body' },
  ],
};
