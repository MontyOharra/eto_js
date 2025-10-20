/**
 * Mock Pipelines API Hook
 * Simulates API calls with in-memory data
 * Matches backend schema - pipelines have NO name/description/status
 */

import { useState } from 'react';
import {
  mockPipelineDefinition,
  mockComplexPipelineDefinition,
  mockSimplePipelineDefinition,
} from '../mocks/pipelineDefinitionMock';
import type {
  PipelineListItem,
  PipelinesListResponse,
  PipelineDetailResponse,
  CreatePipelineRequest,
  CreatePipelineResponse,
  UpdatePipelineRequest,
  UpdatePipelineResponse,
} from '../types';

// Mock data matching backend schema (no name/description/status)
const mockPipelines: PipelineListItem[] = [
  {
    id: 1,
    compiled_plan_id: 101,
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:30:00Z',
  },
  {
    id: 2,
    compiled_plan_id: 102,
    created_at: '2024-01-20T14:15:00Z',
    updated_at: '2024-02-05T16:45:00Z',
  },
  {
    id: 3,
    compiled_plan_id: null, // Not yet compiled
    created_at: '2024-02-10T09:00:00Z',
    updated_at: '2024-02-10T09:00:00Z',
  },
  {
    id: 4,
    compiled_plan_id: 103,
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
    limit = 50,
    offset = 0
  ): Promise<PipelinesListResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(300);

      const start = offset;
      const end = start + limit;
      const items = mockPipelines.slice(start, end);

      return {
        items,
        total: mockPipelines.length,
        limit,
        offset,
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

      // Return specific pipeline definition based on ID
      if (id === 1) {
        return mockPipelineDefinition as PipelineDetailResponse;
      }
      if (id === 2) {
        return mockComplexPipelineDefinition as PipelineDetailResponse;
      }
      if (id === 3) {
        return mockSimplePipelineDefinition as PipelineDetailResponse;
      }

      // For other IDs, check if pipeline exists in list
      const pipeline = mockPipelines.find((p) => p.id === id);
      if (!pipeline) {
        throw new Error('Pipeline not found');
      }

      // Return simple pipeline as fallback for other IDs
      return {
        ...pipeline,
        pipeline_state: mockSimplePipelineDefinition.pipeline_state,
        visual_state: mockSimplePipelineDefinition.visual_state,
      } as PipelineDetailResponse;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch pipeline';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const createPipeline = async (data: CreatePipelineRequest): Promise<CreatePipelineResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(500);

      const newId = mockPipelines.length + 1;
      const newPipeline: PipelineListItem = {
        id: newId,
        compiled_plan_id: null, // Not compiled yet
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      mockPipelines.push(newPipeline);

      return {
        id: newId,
        compiled_plan_id: null,
      };
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
  ): Promise<UpdatePipelineResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(300);

      const index = mockPipelines.findIndex((p) => p.id === id);
      if (index === -1) {
        throw new Error('Pipeline not found');
      }

      // Update the pipeline's updated_at timestamp
      mockPipelines[index] = {
        ...mockPipelines[index],
        updated_at: new Date().toISOString(),
      };

      return {
        id: mockPipelines[index].id,
        compiled_plan_id: mockPipelines[index].compiled_plan_id,
      };
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update pipeline';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
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
    deletePipeline,
    isLoading,
    error,
  };
}
