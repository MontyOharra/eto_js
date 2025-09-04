/**
 * Test service to verify module transformation functionality
 */

import { BackendModuleData, transformBackendModule } from './moduleTransformService';

// Sample backend module data for testing
export const sampleBackendModule: BackendModuleData = {
  id: 'basic_text_cleaner',
  name: 'Basic Text Cleaner',
  description: 'Simple text cleaner with no configuration options',
  version: '1.0.0',
  input_schema: JSON.stringify([
    {
      name: 'input_text',
      type: 'string',
      description: 'Raw text to be cleaned',
      required: true
    }
  ]),
  output_schema: JSON.stringify([
    {
      name: 'cleaned_text',
      type: 'string',
      description: 'Basic cleaned text output'
    }
  ]),
  config_schema: JSON.stringify([]),
  service_endpoint: null,
  handler_name: 'BasicTextCleanerModule',
  max_inputs: 1,
  max_outputs: 1,
  dynamic_inputs: null,
  dynamic_outputs: null,
  color: '#3B82F6',
  category: 'Text Processing',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  is_active: true
};

// Sample backend module with variable inputs/outputs
export const sampleVariableBackendModule: BackendModuleData = {
  id: 'data_combiner',
  name: 'Data Combiner',
  description: 'Combines multiple data inputs into outputs with configurable types',
  version: '1.0.0',
  input_schema: JSON.stringify([
    {
      name: 'input_1',
      type: 'string',
      description: 'First data input',
      required: true,
      dynamicType: {
        configKey: 'input_1_type',
        options: ['string', 'number', 'boolean', 'datetime']
      }
    }
  ]),
  output_schema: JSON.stringify([
    {
      name: 'output_1',
      type: 'string',
      description: 'Combined data output',
      dynamicType: {
        configKey: 'output_1_type',
        options: ['string', 'number', 'boolean', 'datetime']
      }
    }
  ]),
  config_schema: JSON.stringify([
    {
      name: 'combination_method',
      type: 'select',
      description: 'How to combine the input data',
      required: true,
      defaultValue: 'concatenate',
      options: ['concatenate', 'sum', 'average', 'first_non_empty', 'custom']
    }
  ]),
  service_endpoint: null,
  handler_name: 'DataCombinerModule',
  max_inputs: null, // Variable inputs
  max_outputs: null, // Variable outputs
  dynamic_inputs: JSON.stringify({
    enabled: true,
    minNodes: 1,
    maxNodes: 8,
    defaultTemplate: {
      name: 'input_{{index}}',
      type: 'string',
      description: 'Data input {{index}}',
      required: false,
      dynamicType: {
        configKey: 'input_{{index}}_type',
        options: ['string', 'number', 'boolean', 'datetime']
      }
    },
    allowTypeConfiguration: true
  }),
  dynamic_outputs: JSON.stringify({
    enabled: true,
    minNodes: 1,
    maxNodes: 5,
    defaultTemplate: {
      name: 'output_{{index}}',
      type: 'string',
      description: 'Combined output {{index}}',
      dynamicType: {
        configKey: 'output_{{index}}_type',
        options: ['string', 'number', 'boolean', 'datetime']
      }
    },
    allowTypeConfiguration: true
  }),
  color: '#0EA5E9',
  category: 'Data Processing',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  is_active: true
};

/**
 * Test the module transformation functionality
 */
export function testModuleTransformation(): void {
  console.log('Testing module transformation...');
  
  try {
    // Test basic module transformation
    console.log('Backend module:', sampleBackendModule);
    const transformedBasic = transformBackendModule(sampleBackendModule);
    console.log('Transformed basic module:', transformedBasic);
    
    // Test variable module transformation
    console.log('Variable backend module:', sampleVariableBackendModule);
    const transformedVariable = transformBackendModule(sampleVariableBackendModule);
    console.log('Transformed variable module:', transformedVariable);
    
    // Verify key properties
    console.log('Transformation verification:');
    console.log('- Basic module max inputs:', transformedBasic.maxInputs, '(should be 1)');
    console.log('- Variable module max inputs:', transformedVariable.maxInputs, '(should be undefined)');
    console.log('- Variable module has dynamic inputs:', !!transformedVariable.dynamicInputs, '(should be true)');
    console.log('- Variable module has dynamic outputs:', !!transformedVariable.dynamicOutputs, '(should be true)');
    
  } catch (error) {
    console.error('Module transformation test failed:', error);
  }
}