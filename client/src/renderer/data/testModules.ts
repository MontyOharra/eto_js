export interface ModuleInput {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime';
  description: string;
  required: boolean;
  defaultValue?: unknown;
  // For dynamic type nodes
  dynamicType?: {
    configKey: string; // Which config field controls this type
    options: ('string' | 'number' | 'boolean' | 'datetime')[]; // Available type options
  };
}

export interface ModuleOutput {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime';
  description: string;
  required?: boolean; // Optional for outputs, defaults to false
  // For dynamic type nodes
  dynamicType?: {
    configKey: string; // Which config field controls this type
    options: ('string' | 'number' | 'boolean' | 'datetime')[]; // Available type options
  };
}

export interface ModuleConfig {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'textarea';
  description: string;
  required: boolean;
  defaultValue?: unknown;
  options?: string[]; // For select type
  placeholder?: string;
  hidden?: boolean; // Hide from config UI
}

export interface DynamicNodeConfig {
  enabled: boolean;
  minNodes?: number;
  maxNodes?: number;
  defaultTemplate: ModuleInput | ModuleOutput;
  allowTypeConfiguration?: boolean;
}

export interface BaseModuleTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  inputs: ModuleInput[];
  outputs: ModuleOutput[];
  config: ModuleConfig[];
  color: string; // For UI theming
  maxInputs?: number; // null/undefined means unlimited, number means fixed max
  maxOutputs?: number; // null/undefined means unlimited, number means fixed max
  
  // New fields for dynamic behavior
  dynamicInputs?: DynamicNodeConfig;
  dynamicOutputs?: DynamicNodeConfig;
  
  // Function to generate dynamic nodes based on config
  generateNodes?: (config: any) => {
    inputs: ModuleInput[];
    outputs: ModuleOutput[];
  };
}

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
const extractedDataModules: BaseModuleTemplate[] = mockExtractedFields.map(field => ({
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
const orderGenerationModule: BaseModuleTemplate = {
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

// Test data with variable vs fixed input/output scenarios
export const testBaseModules: BaseModuleTemplate[] = [
  // Special pipeline modules first
  ...extractedDataModules,
  orderGenerationModule,
  
  // Separator comment for organization
  // Regular processing modules below
  // 1. Basic Text Cleaner - Fixed single input, single output
  {
    id: "basic_text_cleaner",
    name: "Basic Text Cleaner",
    description: "Simple text cleaner with no configuration options",
    category: "Text Processing",
    color: "#3B82F6", // Blue
    maxInputs: 1, // Fixed single input
    maxOutputs: 1, // Fixed single output
    inputs: [
      {
        name: "input_text",
        type: "string",
        description: "Raw text to be cleaned",
        required: true
      }
    ],
    outputs: [
      {
        name: "cleaned_text",
        type: "string",
        description: "Basic cleaned text output"
      }
    ],
    config: [] // No configuration options
  },
  

  // 3. Text Splitter - Fixed input, variable outputs
  {
    id: "text_splitter",
    name: "Text Splitter",
    description: "Split text into multiple chunks based on various criteria",
    category: "Text Processing",
    color: "#8B5CF6", // Purple
    maxInputs: 1, // Fixed single input
    maxOutputs: undefined, // Variable outputs (can add more)
    inputs: [
      {
        name: "input_text",
        type: "string",
        description: "Text to be split",
        required: true
      }
    ],
    outputs: [
      {
        name: "chunk_1",
        type: "string",
        description: "First text chunk"
      },
      {
        name: "chunk_2",
        type: "string",
        description: "Second text chunk"
      },
      {
        name: "chunk_3",
        type: "string",
        description: "Third text chunk"
      },
      {
        name: "chunk_4",
        type: "string",
        description: "Third text chunk"
      },
      {
        name: "chunk_5",
        type: "string",
        description: "Third text chunk"
      },
      {
        name: "chunk_6",
        type: "string",
        description: "Third text chunk"
      },
      {
        name: "chunk_7",
        type: "string",
        description: "Third text chunk"
      },
      {
        name: "chunk_8",
        type: "string",
        description: "Third text chunk"
      }
    ],
    config: [
      {
        name: "split_method",
        type: "select",
        description: "Method to use for splitting text",
        required: true,
        defaultValue: "sentence",
        options: ["sentence", "paragraph", "word_count", "character_count", "delimiter"]
      },
      {
        name: "chunk_size",
        type: "number",
        description: "Target size for each chunk (words or characters)",
        required: false,
        defaultValue: 100
      },
      {
        name: "custom_delimiter",
        type: "string",
        description: "Custom delimiter for splitting (if delimiter method selected)",
        required: false,
        placeholder: ","
      }
    ]
  },


  // 5. Type Coercion Module - Convert string inputs to other data types
  {
    id: "type_coercion",
    name: "Type Coercion",
    description: "Converts string input to specified data type (number, boolean, datetime)",
    category: "Data Processing",
    color: "#7C3AED", // Purple
    maxInputs: 1, // Fixed single input
    maxOutputs: 1, // Fixed single output
    inputs: [
      {
        name: "input_string",
        type: "string",
        description: "String value to be converted",
        required: true
      }
    ],
    outputs: [
      {
        name: "converted_value",
        type: "string", // Default type, will be updated by generateNodes
        description: "The converted value in the target type"
      }
    ],
    config: [
      {
        name: "output_type",
        type: "select",
        description: "Target data type for conversion (controlled by node dropdown)",
        required: true,
        defaultValue: "string",
        options: ["string", "number", "boolean", "datetime"],
        hidden: true // Hide from config UI since it's controlled by inline dropdown
      },
      {
        name: "date_format",
        type: "string",
        description: "Date format pattern (only used for datetime conversion)",
        required: false,
        defaultValue: "YYYY-MM-DD",
        placeholder: "YYYY-MM-DD HH:mm:ss"
      },
      {
        name: "number_precision",
        type: "number",
        description: "Number of decimal places (only used for number conversion)",
        required: false,
        defaultValue: 2
      },
      {
        name: "boolean_true_values",
        type: "string",
        description: "Comma-separated values that evaluate to true (case-insensitive)",
        required: false,
        defaultValue: "true,yes,1,on",
        placeholder: "true,yes,1,on"
      }
    ],
    // Dynamic node generation based on config
    generateNodes: (config) => {
      const outputType = (config.output_type || 'string') as 'string' | 'number' | 'boolean' | 'datetime';
      
      return {
        inputs: [
          {
            name: "input_string",
            type: "string",
            description: "String value to be converted",
            required: true
          }
        ],
        outputs: [
          {
            name: "converted_value",
            type: outputType,
            description: `The converted ${outputType} value`,
            dynamicType: {
              configKey: 'output_type',
              options: ['string', 'number', 'boolean', 'datetime']
            }
          }
        ]
      };
    }
  },

  // 6. Data Combiner - Variable inputs and outputs with dynamic types
  {
    id: "data_combiner",
    name: "Data Combiner",
    description: "Combines multiple data inputs into outputs with configurable types",
    category: "Data Processing",
    color: "#0EA5E9", // Sky blue
    maxInputs: undefined, // Variable inputs
    maxOutputs: undefined, // Variable outputs
    inputs: [
      {
        name: "input_1",
        type: "string",
        description: "First data input",
        required: true,
        dynamicType: {
          configKey: 'input_1_type',
          options: ['string', 'number', 'boolean', 'datetime']
        }
      }
    ],
    outputs: [
      {
        name: "output_1",
        type: "string",
        description: "Combined data output",
        dynamicType: {
          configKey: 'output_1_type',
          options: ['string', 'number', 'boolean', 'datetime']
        }
      }
    ],
    dynamicInputs: {
      enabled: true,
      minNodes: 1,
      maxNodes: 8,
      defaultTemplate: {
        name: "input_{{index}}",
        type: "string",
        description: "Data input {{index}}",
        required: false,
        dynamicType: {
          configKey: 'input_{{index}}_type',
          options: ['string', 'number', 'boolean', 'datetime']
        }
      },
      allowTypeConfiguration: true
    },
    dynamicOutputs: {
      enabled: true,
      minNodes: 1,
      maxNodes: 5,
      defaultTemplate: {
        name: "output_{{index}}",
        type: "string",
        description: "Combined output {{index}}",
        dynamicType: {
          configKey: 'output_{{index}}_type',
          options: ['string', 'number', 'boolean', 'datetime']
        }
      },
      allowTypeConfiguration: true
    },
    config: [
      {
        name: "input_1_type",
        type: "select",
        description: "Type for input 1",
        required: true,
        defaultValue: "string",
        options: ["string", "number", "boolean", "datetime"],
        hidden: true // Controlled by inline dropdowns
      },
      {
        name: "output_1_type",
        type: "select",
        description: "Type for output 1",
        required: true,
        defaultValue: "string",
        options: ["string", "number", "boolean", "datetime"],
        hidden: true // Controlled by inline dropdowns
      },
      {
        name: "combination_method",
        type: "select",
        description: "How to combine the input data",
        required: true,
        defaultValue: "concatenate",
        options: ["concatenate", "sum", "average", "first_non_empty", "custom"]
      }
    ]
  },

  // 7. Mathematical Calculator - Fixed multiple inputs and outputs
  {
    id: "math_calculator",
    name: "Mathematical Calculator",
    description: "Performs mathematical operations on exactly two numeric inputs",
    category: "Math",
    color: "#EF4444", // Red
    maxInputs: 2, // Fixed two inputs
    maxOutputs: 3, // Fixed three outputs
    inputs: [
      {
        name: "number_a",
        type: "number",
        description: "First number for calculation",
        required: true
      },
      {
        name: "number_b",
        type: "number",
        description: "Second number for calculation",
        required: true
      }
    ],
    outputs: [
      {
        name: "sum",
        type: "number",
        description: "Sum of the two numbers"
      },
      {
        name: "difference",
        type: "number",
        description: "Difference of the two numbers"
      },
      {
        name: "product",
        type: "number",
        description: "Product of the two numbers"
      }
    ],
    config: [
      {
        name: "precision",
        type: "number",
        description: "Number of decimal places for results",
        required: false,
        defaultValue: 2
      },
      {
        name: "include_division",
        type: "boolean",
        description: "Include division result as additional output",
        required: false,
        defaultValue: false
      }
    ]
  }
];

// Export the test modules for the hook
export const testModules = testBaseModules;