/**
 * API service for Transformation Pipeline Server
 */

import { BaseModuleTemplate, BackendModuleInfo, convertBackendModuleToFrontend } from '../types/modules';

const TRANSFORMATION_PIPELINE_API_BASE = 'http://localhost:8080';

export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
}

export interface ModulesResponse {
  success: boolean;
  modules: BackendModuleInfo[];
  message?: string;
}

export class TransformationPipelineApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'TransformationPipelineApiError';
  }
}

/**
 * Fetch all available base modules from the transformation pipeline server
 */
export async function fetchBaseModules(): Promise<BaseModuleTemplate[]> {
  try {
    const response = await fetch(`${TRANSFORMATION_PIPELINE_API_BASE}/api/modules`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new TransformationPipelineApiError(
        `HTTP error! status: ${response.status}`,
        response.status
      );
    }

    const data: ModulesResponse = await response.json();

    if (!data.success) {
      throw new TransformationPipelineApiError(
        data.message || 'Failed to fetch modules'
      );
    }

    // Convert backend modules to frontend format
    const backendModules = data.modules || [];
    const frontendModules = backendModules.map(convertBackendModuleToFrontend);
    
    return frontendModules;
  } catch (error) {
    if (error instanceof TransformationPipelineApiError) {
      throw error;
    }
    
    console.error('Error fetching base modules:', error);
    throw new TransformationPipelineApiError(
      `Failed to fetch modules: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Execute a specific module with given inputs and configuration
 */
export async function executeModule(
  moduleId: string,
  inputs: Record<string, any>,
  config: Record<string, any>
): Promise<Record<string, any>> {
  try {
    const response = await fetch(`${TRANSFORMATION_PIPELINE_API_BASE}/api/modules/${moduleId}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        inputs,
        config,
      }),
    });

    if (!response.ok) {
      throw new TransformationPipelineApiError(
        `HTTP error! status: ${response.status}`,
        response.status
      );
    }

    const data = await response.json();

    if (!data.success) {
      throw new TransformationPipelineApiError(
        data.message || 'Module execution failed'
      );
    }

    return data.outputs || {};
  } catch (error) {
    if (error instanceof TransformationPipelineApiError) {
      throw error;
    }
    
    console.error('Error executing module:', error);
    throw new TransformationPipelineApiError(
      `Failed to execute module: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}


/**
 * Analyze a pipeline using step-based algorithm with separate I/O definitions
 */
export async function analyzePipelineWithSteps(
  modules: Array<{
    id: string;
    templateId: string;
    config: Record<string, any>;
    position: { x: number; y: number };
    nodes: any;
  }>,
  connections: Array<{
    id: string;
    fromModuleId: string;
    fromOutputIndex: number;
    toModuleId: string;
    toInputIndex: number;
  }>,
  inputDefinitions: Array<{
    id: string;
    name: string;
    nodes: any;
  }>,
  outputDefinitions: Array<{
    id: string;
    name: string;
    nodes: any;
  }>
): Promise<{
  success: boolean;
  algorithm: string;
  steps: Record<number, Array<{
    id: string;
    type: string;
    name: string;
    template_id: string;
    entity: any;
  }>>;
  step_assignments: Record<string, number>;
  total_steps: number;
  parallel_opportunities: number;
  input_count: number;
  output_count: number;
  processing_module_count: number;
  total_entities: number;
}> {
  try {
    const response = await fetch(`${TRANSFORMATION_PIPELINE_API_BASE}/api/pipelines/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        modules,
        connections,
        input_definitions: inputDefinitions,
        output_definitions: outputDefinitions,
      }),
    });

    if (!response.ok) {
      throw new TransformationPipelineApiError(
        `HTTP error! status: ${response.status}`,
        response.status
      );
    }

    const data = await response.json();

    if (!data.success) {
      throw new TransformationPipelineApiError(
        data.message || 'Pipeline analysis failed'
      );
    }

    return data;
  } catch (error) {
    if (error instanceof TransformationPipelineApiError) {
      throw error;
    }
    
    console.error('Error analyzing pipeline with steps:', error);
    throw new TransformationPipelineApiError(
      `Failed to analyze pipeline: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Analyze a pipeline for execution planning (legacy method)
 */
export async function analyzePipeline(
  modules: Array<{
    id: string;
    templateId: string;
    config: Record<string, any>;
    position: { x: number; y: number };
    nodes: any;
  }>,
  connections: Array<{
    id: string;
    fromModuleId: string;
    fromOutputIndex: number;
    toModuleId: string;
    toInputIndex: number;
  }>,
  targetModuleId?: string
): Promise<{
  success: boolean;
  target_module: any;
  required_modules: string[];
  execution_plan: {
    steps: Array<{
      step_number: number;
      modules: Array<{
        id: string;
        templateId: string;
        config: Record<string, any>;
      }>;
      parallel: boolean;
    }>;
    parallel_count: number;
    total_modules: number;
  };
  total_steps: number;
  parallel_opportunities: number;
}> {
  try {
    const response = await fetch(`${TRANSFORMATION_PIPELINE_API_BASE}/api/pipelines/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        modules,
        connections,
        target_module_id: targetModuleId,
      }),
    });

    if (!response.ok) {
      throw new TransformationPipelineApiError(
        `HTTP error! status: ${response.status}`,
        response.status
      );
    }

    const data = await response.json();

    if (!data.success) {
      throw new TransformationPipelineApiError(
        data.message || 'Pipeline analysis failed'
      );
    }

    return data;
  } catch (error) {
    if (error instanceof TransformationPipelineApiError) {
      throw error;
    }
    
    console.error('Error analyzing pipeline:', error);
    throw new TransformationPipelineApiError(
      `Failed to analyze pipeline: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Execute a pipeline using step-based dependency analysis with parallel processing
 */
export async function executePipelineWithSteps(
  modules: Array<{
    id: string;
    templateId: string;
    config: Record<string, any>;
    position: { x: number; y: number };
    nodes: any;
  }>,
  connections: Array<{
    id: string;
    fromModuleId: string;
    fromOutputIndex: number;
    toModuleId: string;
    toInputIndex: number;
  }>,
  inputDefinitions: Array<{
    id: string;
    name: string;
    nodes: any;
  }>,
  outputDefinitions: Array<{
    id: string;
    name: string;
    nodes: any;
  }>,
  inputData: Record<string, any>  // Node ID -> value mapping
): Promise<{
  success: boolean;
  analysis: {
    steps: Record<number, Array<{
      id: string;
      type: string;
      name: string;
      template_id: string;
      entity: any;
    }>>;
    output_endpoints: Array<{
      id: string;
      type: string;
      name: string;
      template_id: string;
      entity: any;
    }>;
    total_steps: number;
    parallel_opportunities: number;
  };
  outputs: Record<string, any>;
}> {
  try {
    const response = await fetch(`${TRANSFORMATION_PIPELINE_API_BASE}/api/pipelines/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        modules,
        connections,
        input_definitions: inputDefinitions,
        output_definitions: outputDefinitions,
        input_data: inputData,
      }),
    });

    if (!response.ok) {
      throw new TransformationPipelineApiError(
        `HTTP error! status: ${response.status}`,
        response.status
      );
    }

    const data = await response.json();

    if (!data.success) {
      throw new TransformationPipelineApiError(
        data.message || 'Step-based pipeline execution failed'
      );
    }

    return data;
  } catch (error) {
    if (error instanceof TransformationPipelineApiError) {
      throw error;
    }
    
    console.error('Error executing pipeline with steps:', error);
    throw new TransformationPipelineApiError(
      `Failed to execute pipeline: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Test connection to transformation pipeline server
 */
export async function testConnection(): Promise<boolean> {
  try {
    const response = await fetch(`${TRANSFORMATION_PIPELINE_API_BASE}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return response.ok;
  } catch (error) {
    console.error('Connection test failed:', error);
    return false;
  }
}