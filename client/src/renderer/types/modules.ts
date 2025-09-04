/**
 * Type definitions for transformation pipeline modules
 */

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
  generateNodes?: (config: Record<string, unknown>) => {
    inputs: ModuleInput[];
    outputs: ModuleOutput[];
  };
}