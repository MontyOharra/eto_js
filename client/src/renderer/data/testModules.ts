export interface ModuleInput {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'file';
  description: string;
  required: boolean;
  defaultValue?: any;
}

export interface ModuleOutput {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'file';
  description: string;
}

export interface ModuleConfig {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'textarea';
  description: string;
  required: boolean;
  defaultValue?: any;
  options?: string[]; // For select type
  placeholder?: string;
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
}

// Simplified test data with 3 modules
export const testBaseModules: BaseModuleTemplate[] = [
  // 1. Basic Text Cleaner - No configuration
  {
    id: "basic_text_cleaner",
    name: "Basic Text Cleaner",
    description: "Simple text cleaner with no configuration options",
    category: "Text Processing",
    color: "#3B82F6", // Blue
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
  
  // 2. Advanced Text Cleaner - Boolean configurations
  {
    id: "advanced_text_cleaner",
    name: "Advanced Text Cleaner",
    description: "Text cleaner with configurable cleaning options",
    category: "Text Processing",
    color: "#10B981", // Green
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
        description: "Processed and cleaned text"
      }
    ],
    config: [
      {
        name: "remove_punctuation",
        type: "boolean",
        description: "Remove all punctuation marks",
        required: false,
        defaultValue: true
      },
      {
        name: "normalize_whitespace",
        type: "boolean", 
        description: "Convert multiple spaces to single spaces",
        required: false,
        defaultValue: true
      },
      {
        name: "to_lowercase",
        type: "boolean",
        description: "Convert text to lowercase",
        required: false,
        defaultValue: false
      }
    ]
  },

  // 3. LLM Parser - Dropdown and text input
  {
    id: "llm_parser",
    name: "LLM Text Parser",
    description: "AI-powered text parser with model selection and custom prompts",
    category: "AI/ML",
    color: "#8B5CF6", // Purple
    inputs: [
      {
        name: "input_text",
        type: "string",
        description: "Unstructured text to parse",
        required: true
      }
    ],
    outputs: [
      {
        name: "parsed_data",
        type: "object",
        description: "Structured data extracted from the text"
      },
      {
        name: "confidence_score",
        type: "number",
        description: "Confidence score of the parsing (0-1)"
      }
    ],
    config: [
      {
        name: "model_type",
        type: "select",
        description: "LLM model to use",
        required: true,
        defaultValue: "gpt-4",
        options: ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet", "claude-3-haiku"]
      },
      {
        name: "extraction_prompt",
        type: "string",
        description: "Prompt for the LLM",
        required: true,
        placeholder: "Extract the following information from this text..."
      }
    ]
  },

  // 4. Edge Case Testing Module - Very long name and all config types
  {
    id: "comprehensive_edge_case_testing_module",
    name: "Comprehensive Advanced Multi-Purpose Data Processing and Transformation Pipeline Module",
    description: "This is an extremely comprehensive module designed specifically for testing edge cases in the user interface, featuring an exceptionally long description that spans multiple lines and contains detailed information about various processing capabilities, data transformation features, advanced configuration options, and comprehensive functionality that would typically be found in a complex enterprise-grade data processing system with multiple integration points and extensive customization options.",
    category: "Testing",
    color: "#F59E0B", // Amber
    inputs: [
      {
        name: "primary_input_data",
        type: "string",
        description: "Primary input data stream for comprehensive processing",
        required: true
      },
      {
        name: "secondary_data_source",
        type: "object",
        description: "Secondary data source for advanced processing operations",
        required: false
      }
    ],
    outputs: [
      {
        name: "processed_output",
        type: "object",
        description: "Comprehensively processed and transformed output data"
      },
      {
        name: "processing_metrics",
        type: "object",
        description: "Detailed metrics and analytics from the processing operation"
      },
      {
        name: "error_logs",
        type: "array",
        description: "Comprehensive error logs and debugging information"
      }
    ],
    config: [
      {
        name: "enable_advanced_processing",
        type: "boolean",
        description: "Enable advanced processing capabilities with enhanced algorithms",
        required: false,
        defaultValue: true
      },
      {
        name: "processing_mode",
        type: "select",
        description: "Select the primary processing mode for data transformation",
        required: true,
        defaultValue: "standard",
        options: ["basic", "standard", "advanced", "enterprise", "custom"]
      },
      {
        name: "custom_processing_instructions",
        type: "textarea",
        description: "Provide detailed custom processing instructions and specifications",
        required: false,
        placeholder: "Enter your comprehensive processing instructions here, including any specific requirements, constraints, or special handling procedures..."
      },
      {
        name: "api_endpoint_url",
        type: "string",
        description: "API endpoint URL for external service integration",
        required: true,
        placeholder: "https://api.example.com/v1/processing-endpoint"
      },
      {
        name: "batch_size",
        type: "number",
        description: "Batch size for processing operations (1-10000)",
        required: true,
        defaultValue: 100
      },
      {
        name: "enable_detailed_logging",
        type: "boolean",
        description: "Enable comprehensive detailed logging for debugging and monitoring",
        required: false,
        defaultValue: false
      },
      {
        name: "output_format",
        type: "select",
        description: "Select the desired output format for processed data",
        required: true,
        defaultValue: "json",
        options: ["json", "xml", "csv", "parquet", "avro", "protobuf"]
      },
      {
        name: "timeout_duration",
        type: "number",
        description: "Processing timeout duration in seconds",
        required: false,
        defaultValue: 300
      },
      {
        name: "custom_headers",
        type: "string",
        description: "Custom HTTP headers for API requests (JSON format)",
        required: false,
        placeholder: '{"Authorization": "Bearer token", "Content-Type": "application/json"}'
      }
    ]
  }
];