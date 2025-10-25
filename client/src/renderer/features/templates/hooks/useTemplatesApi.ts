/**
 * Templates API Hook
 * Real API implementation for pdf-templates endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import { TemplateListItem } from '../types';
import {
  GetTemplatesQueryParams,
  GetTemplateDetailResponse,
  PostTemplateCreateRequest,
  PostTemplateCreateResponse,
  PutTemplateUpdateRequest,
  PutTemplateUpdateResponse,
  PostTemplateActivateResponse,
  PostTemplateDeactivateResponse,
  GetTemplateVersionsResponse,
  GetTemplateVersionDetailResponse,
  PostTemplateSimulateRequest,
  PostTemplateSimulateResponse,
} from '../api/types';

export function useTemplatesApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = API_CONFIG.ENDPOINTS.TEMPLATES;

  /**
   * Helper to handle API calls with loading and error states
   */
  const withLoadingAndError = useCallback(
    async <T,>(apiCall: () => Promise<T>): Promise<T> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiCall();
        return result;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * GET /api/pdf-templates
   * List templates with filtering and sorting
   */
  const getTemplates = useCallback(
    async (params?: GetTemplatesQueryParams): Promise<TemplateListItem[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<TemplateListItem[]>(baseUrl, {
          params: {
            status: params?.status,
            sort_by: params?.sort_by,
            sort_order: params?.sort_order,
          },
        });
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/pdf-templates/{id}
   * Get template details
   */
  const getTemplateDetail = useCallback(
    async (templateId: number): Promise<GetTemplateDetailResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<GetTemplateDetailResponse>(
          `${baseUrl}/${templateId}`
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/pdf-templates
   * Create new template
   */
  const createTemplate = useCallback(
    async (request: PostTemplateCreateRequest): Promise<PostTemplateCreateResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<PostTemplateCreateResponse>(
          baseUrl,
          request
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * PUT /api/pdf-templates/{id}
   * Update template (creates new version)
   */
  const updateTemplate = useCallback(
    async (
      templateId: number,
      request: PutTemplateUpdateRequest
    ): Promise<PutTemplateUpdateResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.put<PutTemplateUpdateResponse>(
          `${baseUrl}/${templateId}`,
          request
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * DELETE /api/pdf-templates/{id}
   * Delete template
   */
  const deleteTemplate = useCallback(
    async (templateId: number): Promise<void> => {
      return withLoadingAndError(async () => {
        await apiClient.delete(`${baseUrl}/${templateId}`);
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/pdf-templates/{id}/activate
   * Activate template
   */
  const activateTemplate = useCallback(
    async (templateId: number): Promise<PostTemplateActivateResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<PostTemplateActivateResponse>(
          `${baseUrl}/${templateId}/activate`
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/pdf-templates/{id}/deactivate
   * Deactivate template
   */
  const deactivateTemplate = useCallback(
    async (templateId: number): Promise<PostTemplateDeactivateResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<PostTemplateDeactivateResponse>(
          `${baseUrl}/${templateId}/deactivate`
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/pdf-templates/{id}/versions
   * List all versions
   */
  const getTemplateVersions = useCallback(
    async (templateId: number): Promise<GetTemplateVersionsResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<GetTemplateVersionsResponse>(
          `${baseUrl}/${templateId}/versions`
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/pdf-templates/{id}/versions/{version_id}
   * Get version detail
   */
  const getTemplateVersionDetail = useCallback(
    async (
      templateId: number,
      versionId: number
    ): Promise<GetTemplateVersionDetailResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<GetTemplateVersionDetailResponse>(
          `${baseUrl}/${templateId}/versions/${versionId}`
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/pdf-templates/simulate
   * Simulate full ETO process
   */
  const simulateTemplate = useCallback(
    async (request: PostTemplateSimulateRequest): Promise<PostTemplateSimulateResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<PostTemplateSimulateResponse>(
          `${baseUrl}/simulate`,
          request
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  return {
    // State
    isLoading,
    error,

    // API methods
    getTemplates,
    getTemplateDetail,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    activateTemplate,
    deactivateTemplate,
    getTemplateVersions,
    getTemplateVersionDetail,
    simulateTemplate,
  };
}
