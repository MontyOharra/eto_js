import { BaseModuleTemplate } from '../types/modules';

// Mock extracted data fields (in real system, this would come from template extraction results)
export const mockExtractedFields = [
  { name: 'hawb', displayName: 'HAWB Number', sampleValue: 'HAW123456789' },
  { name: 'carrier_name', displayName: 'Carrier Name', sampleValue: 'Forward Air, Inc' },
  { name: 'pickup_address', displayName: 'Pickup Address', sampleValue: '1234 Main St, Dallas, TX 75201' },
  { name: 'pickup_phone', displayName: 'Pickup Phone', sampleValue: '(555) 123-4567' },
  { name: 'delivery_address', displayName: 'Delivery Address', sampleValue: '5678 Oak Ave, Houston, TX 77001' },
  { name: 'delivery_phone', displayName: 'Delivery Phone', sampleValue: '(555) 987-6543' },
  { name: 'weight', displayName: 'Weight', sampleValue: '25.5' },
  { name: 'dimensions', displayName: 'Dimensions', sampleValue: '12x8x6' },
  { name: 'service_type', displayName: 'Service Type', sampleValue: 'Standard Ground' },
  { name: 'tracking_number', displayName: 'Tracking Number', sampleValue: 'TRK987654321' }
];

// Mock order fields (what the final order needs)
export const mockOrderFields = [
  { name: 'order_number', displayName: 'Order Number', required: true, type: 'string' },
  { name: 'customer_name', displayName: 'Customer Name', required: true, type: 'string' },
  { name: 'origin_address', displayName: 'Origin Address', required: true, type: 'string' },
  { name: 'destination_address', displayName: 'Destination Address', required: true, type: 'string' },
  { name: 'package_weight', displayName: 'Package Weight', required: true, type: 'number' },
  { name: 'package_dimensions', displayName: 'Package Dimensions', required: false, type: 'string' },
  { name: 'service_level', displayName: 'Service Level', required: true, type: 'string' },
  { name: 'special_instructions', displayName: 'Special Instructions', required: false, type: 'string' }
];

// Generate extracted data modules
export const extractedDataModules: BaseModuleTemplate[] = mockExtractedFields.map(field => ({
  id: `extracted_${field.name}`,
  name: `Extracted: ${field.displayName}`,
  description: `Outputs the extracted ${field.displayName} from the PDF processing`,
  category: 'Extracted Data',
  color: '#059669', // Emerald green
  maxInputs: 0, // No inputs - these are data sources
  maxOutputs: 1, // Fixed single output
  inputs: [],
  outputs: [
    {
      name: field.name,
      type: 'string', // For now, all extracted data is string
      description: `The extracted ${field.displayName} value`
    }
  ],
  config: [
    {
      name: 'test_value',
      type: 'string',
      description: 'Test value (for development only)',
      required: false,
      defaultValue: field.sampleValue,
      placeholder: `Enter test ${field.displayName}...`
    }
  ]
}));

// Create order generation module
export const orderGenerationModule: BaseModuleTemplate = {
  id: 'order_generation',
  name: 'Generate Order',
  description: 'Final step: Creates an order from the processed data. Every pipeline must end here.',
  category: 'Order Processing',
  color: '#DC2626', // Red
  maxInputs: undefined, // Variable inputs - can accept multiple data sources
  maxOutputs: 0, // No outputs - this is the final destination
  inputs: mockOrderFields.map(field => ({
    name: field.name,
    type: field.type as 'string' | 'number' | 'boolean' | 'datetime',
    description: `Input for ${field.displayName}`,
    required: field.required
  })),
  outputs: [],
  config: [
    {
      name: 'order_type',
      type: 'select',
      description: 'Type of order to generate',
      required: true,
      defaultValue: 'shipping',
      options: ['shipping', 'logistics', 'freight', 'courier']
    },
    {
      name: 'auto_assign_number',
      type: 'boolean',
      description: 'Automatically assign order number if not provided',
      required: false,
      defaultValue: true
    },
    {
      name: 'validation_level',
      type: 'select',
      description: 'Data validation strictness',
      required: true,
      defaultValue: 'standard',
      options: ['strict', 'standard', 'lenient']
    }
  ]
};

// Export the test modules array for the hook
export const testModules: BaseModuleTemplate[] = [
  ...extractedDataModules,
  orderGenerationModule
];

