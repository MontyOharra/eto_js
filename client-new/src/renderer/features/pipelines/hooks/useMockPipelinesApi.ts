/**
 * Mock Pipelines API Hook
 * Simulates API calls with in-memory data
 */

import { useState } from 'react';
import type {
  PipelineListItem,
  PipelinesListResponse,
  PipelineDetailResponse,
  CreatePipelineRequest,
  UpdatePipelineRequest,
  PipelineStatus,
} from '../types';

// Mock data
const mockPipelines: PipelineListItem[] = [
  {
    id: 1,
    name: 'Standard Data Extraction',
    description: 'Extract and transform data from standard AWB documents',
    status: 'active',
    current_version: {
      version_id: 1,
      version_num: 1,
      usage_count: 145,
    },
    total_versions: 1,
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:30:00Z',
  },
  {
    id: 2,
    name: 'Advanced Field Processing',
    description: 'Complex transformation pipeline with validation and formatting',
    status: 'active',
    current_version: {
      version_id: 3,
      version_num: 3,
      usage_count: 89,
    },
    total_versions: 3,
    created_at: '2024-01-20T14:15:00Z',
    updated_at: '2024-02-05T16:45:00Z',
  },
  {
    id: 3,
    name: 'Simple Text Cleanup',
    description: 'Basic text trimming and normalization pipeline',
    status: 'draft',
    current_version: {
      version_id: 1,
      version_num: 1,
      usage_count: 0,
    },
    total_versions: 1,
    created_at: '2024-02-10T09:00:00Z',
    updated_at: '2024-02-10T09:00:00Z',
  },
  {
    id: 4,
    name: 'Legacy Format Converter',
    description: 'Convert old format data to new structure',
    status: 'inactive',
    current_version: {
      version_id: 2,
      version_num: 2,
      usage_count: 234,
    },
    total_versions: 2,
    created_at: '2023-11-05T11:20:00Z',
    updated_at: '2024-01-08T13:30:00Z',
  },
];

export function useMockPipelinesApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Simulate network delay
  const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  const getPipelines = async (
    page = 1,
    pageSize = 50
  ): Promise<PipelinesListResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(300);

      const start = (page - 1) * pageSize;
      const end = start + pageSize;
      const items = mockPipelines.slice(start, end);

      return {
        items,
        total: mockPipelines.length,
        page,
        page_size: pageSize,
      };
    } catch (err) {
      const errorMessage = 'Failed to fetch pipelines';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const getPipeline = async (id: number): Promise<PipelineDetailResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(200);

      const pipeline = mockPipelines.find((p) => p.id === id);
      if (!pipeline) {
        throw new Error('Pipeline not found');
      }

      // Return detailed pipeline with mock transformation data
      return {
        pipeline: {
          ...pipeline,
          entry_points: [
            {
              node_id: 'entry_hawb',
              name: 'hawb',
              type: 'str',
            },
            {
              node_id: 'entry_carrier',
              name: 'carrier',
              type: 'str',
            },
          ],
          modules: [
            {
              module_instance_id: 'module_1',
              module_id: 'trim_text',
              config: {},
              inputs: [
                {
                  node_id: 'input_1',
                  name: 'text',
                  type: 'str',
                },
              ],
              outputs: [
                {
                  node_id: 'output_1',
                  name: 'trimmed_text',
                  type: 'str',
                },
              ],
            },
          ],
          connections: [
            {
              connection_id: 'conn_1',
              source_node_id: 'entry_hawb',
              target_node_id: 'module_1',
              source_pin_id: 'entry_hawb',
              target_pin_id: 'input_1',
            },
          ],
          visual_state: {
            positions: {
              entry_hawb: { x: 50, y: 50 },
              entry_carrier: { x: 50, y: 170 },
              module_1: { x: 400, y: 100 },
            },
          },
        },
      };
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch pipeline';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const createPipeline = async (data: CreatePipelineRequest): Promise<PipelineListItem> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(500);

      const newPipeline: PipelineListItem = {
        id: mockPipelines.length + 1,
        name: data.name,
        description: data.description || null,
        status: 'draft',
        current_version: {
          version_id: 1,
          version_num: 1,
          usage_count: 0,
        },
        total_versions: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      mockPipelines.push(newPipeline);

      return newPipeline;
    } catch (err) {
      const errorMessage = 'Failed to create pipeline';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const updatePipeline = async (
    id: number,
    data: UpdatePipelineRequest
  ): Promise<PipelineListItem> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(300);

      const index = mockPipelines.findIndex((p) => p.id === id);
      if (index === -1) {
        throw new Error('Pipeline not found');
      }

      mockPipelines[index] = {
        ...mockPipelines[index],
        ...data,
        updated_at: new Date().toISOString(),
      };

      return mockPipelines[index];
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update pipeline';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const activatePipeline = async (id: number): Promise<void> => {
    await updatePipeline(id, { status: 'active' });
  };

  const deactivatePipeline = async (id: number): Promise<void> => {
    await updatePipeline(id, { status: 'inactive' });
  };

  const deletePipeline = async (id: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(300);

      const index = mockPipelines.findIndex((p) => p.id === id);
      if (index === -1) {
        throw new Error('Pipeline not found');
      }

      mockPipelines.splice(index, 1);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to delete pipeline';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    getPipelines,
    getPipeline,
    createPipeline,
    updatePipeline,
    activatePipeline,
    deactivatePipeline,
    deletePipeline,
    isLoading,
    error,
  };
}
