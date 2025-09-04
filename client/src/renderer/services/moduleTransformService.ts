/**
 * Service for transforming backend module definitions to frontend format
 */

import { BaseModuleTemplate, ModuleInput, ModuleOutput, ModuleConfig, DynamicNodeConfig } from '../types/modules';

export interface BackendModuleData {
  id: string;
  name: string;
  description: string;
  version: string;
  input_schema: string;
  output_schema: string;
  config_schema: string | null;
  service_endpoint: string | null;
  handler_name: string;
  max_inputs: number | null;
  max_outputs: number | null;
  dynamic_inputs: string | null;
  dynamic_outputs: string | null;
  color: string;
  category: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

/**
 * Convert snake_case to camelCase
 */
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
}

/**
 * Convert backend module data to frontend BaseModuleTemplate format
 */
export function transformBackendModule(backendModule: BackendModuleData): BaseModuleTemplate {
  try {
    // Parse JSON schemas
    const inputs: ModuleInput[] = JSON.parse(backendModule.input_schema || '[]');
    const outputs: ModuleOutput[] = JSON.parse(backendModule.output_schema || '[]');
    const config: ModuleConfig[] = JSON.parse(backendModule.config_schema || '[]');
    
    // Parse dynamic configurations
    let dynamicInputs: DynamicNodeConfig | undefined;
    let dynamicOutputs: DynamicNodeConfig | undefined;
    
    if (backendModule.dynamic_inputs) {
      const parsed = JSON.parse(backendModule.dynamic_inputs);
      dynamicInputs = {
        enabled: parsed.enabled,
        minNodes: parsed.minNodes,
        maxNodes: parsed.maxNodes,
        defaultTemplate: parsed.defaultTemplate,
        allowTypeConfiguration: parsed.allowTypeConfiguration
      };
    }
    
    if (backendModule.dynamic_outputs) {
      const parsed = JSON.parse(backendModule.dynamic_outputs);
      dynamicOutputs = {
        enabled: parsed.enabled,
        minNodes: parsed.minNodes,
        maxNodes: parsed.maxNodes,
        defaultTemplate: parsed.defaultTemplate,
        allowTypeConfiguration: parsed.allowTypeConfiguration
      };
    }
    
    // Transform to frontend format
    const frontendModule: BaseModuleTemplate = {
      id: backendModule.id,
      name: backendModule.name,
      description: backendModule.description,
      category: backendModule.category,
      inputs: inputs.map(input => ({
        name: input.name,
        type: input.type,
        description: input.description,
        required: input.required,
        defaultValue: input.defaultValue,
        dynamicType: input.dynamicType
      })),
      outputs: outputs.map(output => ({
        name: output.name,
        type: output.type,
        description: output.description,
        dynamicType: output.dynamicType
      })),
      config: config.map(configItem => ({
        name: configItem.name,
        type: configItem.type,
        description: configItem.description,
        required: configItem.required,
        defaultValue: configItem.defaultValue,
        options: configItem.options,
        placeholder: configItem.placeholder,
        hidden: configItem.hidden
      })),
      color: backendModule.color,
      maxInputs: backendModule.max_inputs === null ? undefined : backendModule.max_inputs,
      maxOutputs: backendModule.max_outputs === null ? undefined : backendModule.max_outputs,
      dynamicInputs,
      dynamicOutputs
    };
    
    return frontendModule;
    
  } catch (error) {
    console.error(`Error transforming backend module ${backendModule.id}:`, error);
    throw new Error(`Failed to transform module ${backendModule.id}: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Transform multiple backend modules to frontend format
 */
export function transformBackendModules(backendModules: BackendModuleData[]): BaseModuleTemplate[] {
  const transformed: BaseModuleTemplate[] = [];
  const errors: string[] = [];
  
  for (const backendModule of backendModules) {
    try {
      const frontendModule = transformBackendModule(backendModule);
      transformed.push(frontendModule);
    } catch (error) {
      errors.push(`Module ${backendModule.id}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      console.error(`Failed to transform module ${backendModule.id}:`, error);
    }
  }
  
  if (errors.length > 0) {
    console.warn(`Some modules failed to transform:`, errors);
  }
  
  return transformed;
}

/**
 * Validate that a transformed module has required fields
 */
export function validateTransformedModule(module: BaseModuleTemplate): boolean {
  const required = ['id', 'name', 'description', 'category', 'inputs', 'outputs', 'config', 'color'];
  
  for (const field of required) {
    if (!(field in module) || module[field as keyof BaseModuleTemplate] === undefined) {
      console.error(`Transformed module ${module.id} missing required field: ${field}`);
      return false;
    }
  }
  
  return true;
}