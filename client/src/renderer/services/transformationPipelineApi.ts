/**
 * API service for Transformation Pipeline Server
 */

import { BaseModuleTemplate } from '../types/modules';

const TRANSFORMATION_PIPELINE_API_BASE = 'http://localhost:8090';

export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
}

export interface ModulesResponse {
  success: boolean;
  modules: BaseModuleTemplate[];
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

    // Backend API already returns modules in frontend format (camelCase)
    const modules = data.modules || [];
    
    return modules;
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
 * Get dynamic outputs for a module based on configuration
 */
export async function getDynamicOutputs(
  moduleId: string,
  config: Record<string, any>
): Promise<{ outputs: any[], supports_dynamic: boolean }> {
  try {
    const response = await fetch(`${TRANSFORMATION_PIPELINE_API_BASE}/api/modules/${moduleId}/outputs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
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
        data.message || 'Failed to get dynamic outputs'
      );
    }

    return {
      outputs: data.outputs || [],
      supports_dynamic: data.supports_dynamic || false
    };
  } catch (error) {
    if (error instanceof TransformationPipelineApiError) {
      throw error;
    }
    
    console.error('Error getting dynamic outputs:', error);
    throw new TransformationPipelineApiError(
      `Failed to get dynamic outputs: ${error instanceof Error ? error.message : 'Unknown error'}`
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