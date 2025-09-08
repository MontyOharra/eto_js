/**
 * Type definitions for transformation pipeline modules
 */

export interface ModuleInput {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime' | 'undefined';
  description: string;
  required: boolean;
  defaultValue?: unknown;
  // For dynamic type nodes
  dynamicType?: {
    configKey: string; // Which config field controls this type
    options: ('string' | 'number' | 'boolean' | 'datetime' | 'undefined')[]; // Available type options
  };
}

export interface ModuleOutput {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime' | 'undefined';
  description: string;
  required?: boolean; // Optional for outputs, defaults to false
  // For dynamic type nodes
  dynamicType?: {
    configKey: string; // Which config field controls this type
    options: ('string' | 'number' | 'boolean' | 'datetime' | 'undefined')[]; // Available type options
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

// New backend schema format
export interface NodeSchema {
  defaultName: string;
  type: 'string' | 'number' | 'boolean' | 'datetime' | 'undefined';
}

export interface NodeConfiguration {
  nodes: NodeSchema[];
  dynamic?: {
    maxNodes?: number;
    defaultNode: NodeSchema;
  } | null;
  allowedTypes: ('string' | 'number' | 'boolean' | 'datetime' | 'undefined')[];
}

// Backend response format (new schema)
export interface BackendModuleInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  color: string;
  version: string;
  inputConfig: NodeConfiguration;
  outputConfig: NodeConfiguration;
  config: ModuleConfig[];
}

// Frontend usage format (legacy format for compatibility)
export interface BaseModuleTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  inputs: ModuleInput[];
  outputs: ModuleOutput[];
  config: ModuleConfig[];
  color: string; // For UI theming
  version?: string;
  maxInputs?: number; // null/undefined means unlimited, number means fixed max
  maxOutputs?: number; // null/undefined means unlimited, number means fixed max
  
  // New fields for dynamic behavior
  dynamicInputs?: DynamicNodeConfig;
  dynamicOutputs?: DynamicNodeConfig;
  
  // Type configuration support (new schema)
  allowInputTypeConfig?: boolean;
  allowOutputTypeConfig?: boolean;
  inputAllowedTypes?: ('string' | 'number' | 'boolean' | 'datetime' | 'undefined')[];
  outputAllowedTypes?: ('string' | 'number' | 'boolean' | 'datetime' | 'undefined')[];
  
  // Function to generate dynamic nodes based on config
  generateNodes?: (config: Record<string, unknown>) => {
    inputs: ModuleInput[];
    outputs: ModuleOutput[];
  };
}

/**
 * Convert backend module format to frontend format
 */
export function convertBackendModuleToFrontend(backendModule: BackendModuleInfo): BaseModuleTemplate {
  // Convert NodeConfiguration to ModuleInput/Output arrays
  const inputs: ModuleInput[] = backendModule.inputConfig.nodes.map((node, index) => ({
    name: node.defaultName,
    type: node.type,
    description: `Input ${index + 1}`,
    required: true,
  }));

  const outputs: ModuleOutput[] = backendModule.outputConfig.nodes.map((node, index) => ({
    name: node.defaultName,
    type: node.type,
    description: `Output ${index + 1}`,
    required: false,
  }));

  // Convert dynamic configuration if present
  const dynamicInputs: DynamicNodeConfig | undefined = backendModule.inputConfig.dynamic ? {
    enabled: true,
    maxNodes: backendModule.inputConfig.dynamic.maxNodes,
    allowTypeConfiguration: backendModule.inputConfig.allowedTypes.length === 0 || backendModule.inputConfig.allowedTypes.length > 1,
    defaultTemplate: {
      name: backendModule.inputConfig.dynamic.defaultNode.defaultName,
      type: backendModule.inputConfig.dynamic.defaultNode.type,
      description: 'Dynamic input',
      required: true,
    },
  } : undefined;

  const dynamicOutputs: DynamicNodeConfig | undefined = backendModule.outputConfig.dynamic ? {
    enabled: true,
    maxNodes: backendModule.outputConfig.dynamic.maxNodes,
    allowTypeConfiguration: backendModule.outputConfig.allowedTypes.length === 0 || backendModule.outputConfig.allowedTypes.length > 1,
    defaultTemplate: {
      name: backendModule.outputConfig.dynamic.defaultNode.defaultName,
      type: backendModule.outputConfig.dynamic.defaultNode.type,
      description: 'Dynamic output',
      required: false,
    },
  } : undefined;

  return {
    id: backendModule.id,
    name: backendModule.name,
    description: backendModule.description,
    category: backendModule.category,
    color: backendModule.color,
    version: backendModule.version,
    inputs,
    outputs,
    config: backendModule.config,
    maxInputs: backendModule.inputConfig.dynamic?.maxNodes,
    maxOutputs: backendModule.outputConfig.dynamic?.maxNodes,
    dynamicInputs,
    dynamicOutputs,
    // Add new type configuration fields
    allowInputTypeConfig: backendModule.inputConfig.allowedTypes.length === 0 || backendModule.inputConfig.allowedTypes.length > 1,
    allowOutputTypeConfig: backendModule.outputConfig.allowedTypes.length === 0 || backendModule.outputConfig.allowedTypes.length > 1,
    inputAllowedTypes: backendModule.inputConfig.allowedTypes,
    outputAllowedTypes: backendModule.outputConfig.allowedTypes,
  };
}