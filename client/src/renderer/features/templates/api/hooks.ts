/**
 * Templates API Hooks
 * TanStack Query hooks for template operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import {
  GetTemplatesQueryParams,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  SimulateTemplateRequest,
  SimulateTemplateResponse,
} from './types';
import { TemplateListItem, TemplateDetail, TemplateVersionDetail } from '../types';

const baseUrl = API_CONFIG.ENDPOINTS.TEMPLATES;

// ============================================================================
// Query Hooks (GET operations)
// ============================================================================

/**
 * Fetch list of templates with filtering and sorting
 * Returns array of templates (backend doesn't paginate templates yet)
 */
export function useTemplates(params?: GetTemplatesQueryParams) {
  return useQuery({
    queryKey: ['templates', params],
    queryFn: async (): Promise<TemplateListItem[]> => {
      const response = await apiClient.get<TemplateListItem[]>(baseUrl, {
        params: {
          status: params?.status,
          sort_by: params?.sort_by,
          sort_order: params?.sort_order,
        },
      });
      return response.data;
    },
    staleTime: 60 * 1000, // Consider data stale after 1 minute
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}

/**
 * Fetch detailed information for a single template
 * Includes all versions list (IDs only) but not version content
 */
export function useTemplateDetail(templateId: number | null) {
  return useQuery({
    queryKey: ['template', templateId],
    queryFn: async (): Promise<TemplateDetail> => {
      if (!templateId) {
        throw new Error('No template ID provided');
      }

      const response = await apiClient.get<TemplateDetail>(
        `${baseUrl}/${templateId}`
      );
      return response.data;
    },
    enabled: !!templateId, // Only run query if templateId exists
    staleTime: 60 * 1000, // Consider data stale after 1 minute
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}

/**
 * Fetch detailed information for a specific template version
 * Includes full version content (signature objects, fields, pipeline)
 */
export function useTemplateVersionDetail(versionId: number | null) {
  return useQuery({
    queryKey: ['template-version', versionId],
    queryFn: async (): Promise<TemplateVersionDetail> => {
      if (!versionId) {
        throw new Error('No version ID provided');
      }

      const response = await apiClient.get<TemplateVersionDetail>(
        `${baseUrl}/versions/${versionId}`
      );
      return response.data;
    },
    enabled: !!versionId, // Only run query if versionId exists
    staleTime: Infinity, // Template versions never change once created
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });
}

// ============================================================================
// Mutation Hooks (POST/PUT/DELETE operations)
// ============================================================================

/**
 * Create new template
 * Requires source PDF to be uploaded first
 */
export function useCreateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: CreateTemplateRequest
    ): Promise<TemplateDetail> => {
      const response = await apiClient.post<TemplateDetail>(
        baseUrl,
        request
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate templates list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
}

/**
 * Update template (creates new version)
 * Can update metadata and/or create new version with new content
 */
export function useUpdateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      templateId,
      request,
    }: {
      templateId: number;
      request: UpdateTemplateRequest;
    }): Promise<TemplateDetail> => {
      const response = await apiClient.put<TemplateDetail>(
        `${baseUrl}/${templateId}`,
        request
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate templates list and specific template detail
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      queryClient.invalidateQueries({ queryKey: ['template', variables.templateId] });
    },
  });
}

/**
 * Delete template
 * Permanently removes template and all versions
 */
export function useDeleteTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (templateId: number): Promise<void> => {
      await apiClient.delete(`${baseUrl}/${templateId}`);
    },
    onSuccess: () => {
      // Invalidate templates list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
}

/**
 * Activate template
 * Makes template available for ETO run matching
 */
export function useActivateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (templateId: number): Promise<TemplateDetail> => {
      const response = await apiClient.post<TemplateDetail>(
        `${baseUrl}/${templateId}/activate`
      );
      return response.data;
    },
    onSuccess: (_, templateId) => {
      // Invalidate templates list and specific template detail
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      queryClient.invalidateQueries({ queryKey: ['template', templateId] });
    },
  });
}

/**
 * Deactivate template
 * Removes template from ETO run matching (existing runs unaffected)
 */
export function useDeactivateTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (templateId: number): Promise<TemplateDetail> => {
      const response = await apiClient.post<TemplateDetail>(
        `${baseUrl}/${templateId}/deactivate`
      );
      return response.data;
    },
    onSuccess: (_, templateId) => {
      // Invalidate templates list and specific template detail
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      queryClient.invalidateQueries({ queryKey: ['template', templateId] });
    },
  });
}

/**
 * Simulate full ETO process
 * Testing/preview only - does not create template or run
 *
 * Accepts JSON body with pre-extracted PDF objects
 * Returns extraction results and pipeline execution results
 */
export function useSimulateTemplate() {
  return useMutation({
    mutationFn: async (
      request: SimulateTemplateRequest
    ): Promise<SimulateTemplateResponse> => {
      const response = await apiClient.post<SimulateTemplateResponse>(
        `${baseUrl}/simulate`,
        request,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      return response.data;
    },
    // No cache invalidation needed - this is a one-off testing operation
  });
}
