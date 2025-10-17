/**
 * Mock Templates API Hook
 * Simulates API calls with realistic delays and returns mock data
 */

import { useState } from 'react';
import {
  GetTemplatesQueryParams,
  GetTemplatesResponse,
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
import {
  allMockTemplates,
  mockTemplatesByStatus,
  mockTemplateDetailsById,
  mockTemplateVersions,
  mockTemplateVersionDetail,
  mockCreateResponse,
  mockSimulateResponse,
} from '../mocks/data';
import { TemplateListItem, TemplateStatus } from '../types';

// Simulated network delay (300-800ms)
const simulateDelay = () =>
  new Promise((resolve) => setTimeout(resolve, Math.random() * 500 + 300));

export function useMockTemplatesApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ==========================================================================
  // GET /pdf-templates - List templates with filtering and pagination
  // ==========================================================================
  const getTemplates = async (
    params?: GetTemplatesQueryParams
  ): Promise<GetTemplatesResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Filter by status if provided
      let filteredTemplates: TemplateListItem[] = params?.status
        ? mockTemplatesByStatus[params.status]
        : allMockTemplates;

      // Sort
      const sortBy = params?.sort_by || 'name';
      const sortOrder = params?.sort_order || 'asc';

      filteredTemplates = [...filteredTemplates].sort((a, b) => {
        let aValue: any;
        let bValue: any;

        switch (sortBy) {
          case 'name':
            aValue = a.name.toLowerCase();
            bValue = b.name.toLowerCase();
            break;
          case 'status':
            aValue = a.status;
            bValue = b.status;
            break;
          case 'usage_count':
            aValue = a.current_version.usage_count;
            bValue = b.current_version.usage_count;
            break;
          default:
            aValue = a.id;
            bValue = b.id;
        }

        if (sortOrder === 'asc') {
          return aValue > bValue ? 1 : -1;
        } else {
          return aValue < bValue ? 1 : -1;
        }
      });

      // Pagination
      const limit = params?.limit || 50;
      const offset = params?.offset || 0;
      const paginatedTemplates = filteredTemplates.slice(offset, offset + limit);

      return {
        items: paginatedTemplates,
        total: filteredTemplates.length,
        limit,
        offset,
      };
    } catch (err) {
      const errorMessage = 'Failed to fetch templates';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // GET /pdf-templates/{id} - Get template details
  // ==========================================================================
  const getTemplateDetail = async (
    templateId: number
  ): Promise<GetTemplateDetailResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      const detail = mockTemplateDetailsById[templateId];

      if (!detail) {
        throw new Error('Template not found');
      }

      return detail;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch template details';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // POST /pdf-templates - Create new template
  // ==========================================================================
  const createTemplate = async (
    request: PostTemplateCreateRequest
  ): Promise<PostTemplateCreateResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate required fields
      if (!request.name || request.name.length < 1 || request.name.length > 255) {
        throw new Error('Template name must be between 1 and 255 characters');
      }

      if (request.signature_objects.length < 1) {
        throw new Error('At least one signature object is required');
      }

      if (request.extraction_fields.length < 1) {
        throw new Error('At least one extraction field is required');
      }

      // Return mock create response with incremented ID
      return {
        ...mockCreateResponse,
        id: mockCreateResponse.id + Math.floor(Math.random() * 1000),
        name: request.name,
      };
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create template';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // PUT /pdf-templates/{id} - Update template (creates new version)
  // ==========================================================================
  const updateTemplate = async (
    templateId: number,
    request: PutTemplateUpdateRequest
  ): Promise<PutTemplateUpdateResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate template exists
      const template = allMockTemplates.find((t) => t.id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      // Validate required fields
      if (request.signature_objects.length < 1) {
        throw new Error('At least one signature object is required');
      }

      if (request.extraction_fields.length < 1) {
        throw new Error('At least one extraction field is required');
      }

      // Return mock update response
      return {
        id: templateId,
        name: request.name || template.name,
        status: template.status,
        current_version_id: template.current_version.version_id + 1,
        current_version_num: template.current_version.version_num + 1,
        pipeline_definition_id: 300 + templateId,
      };
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update template';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // DELETE /pdf-templates/{id} - Delete template
  // ==========================================================================
  const deleteTemplate = async (templateId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate template exists
      const template = allMockTemplates.find((t) => t.id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      // Validate deletion rules
      if (
        template.status !== 'draft' &&
        template.current_version.usage_count > 0
      ) {
        throw new Error(
          'Cannot delete template with usage history. Deactivate instead.'
        );
      }

      // Success - 204 No Content
      console.log(`Deleted template ${templateId}`);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to delete template';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // POST /pdf-templates/{id}/activate - Activate template
  // ==========================================================================
  const activateTemplate = async (
    templateId: number
  ): Promise<PostTemplateActivateResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate template exists
      const template = allMockTemplates.find((t) => t.id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      // Validate has finalized version
      if (template.total_versions < 1) {
        throw new Error('Template has no finalized versions');
      }

      return {
        id: templateId,
        status: 'active',
        current_version_id: template.current_version.version_id,
      };
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to activate template';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // POST /pdf-templates/{id}/deactivate - Deactivate template
  // ==========================================================================
  const deactivateTemplate = async (
    templateId: number
  ): Promise<PostTemplateDeactivateResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate template exists
      const template = allMockTemplates.find((t) => t.id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      return {
        id: templateId,
        status: 'inactive',
        current_version_id: template.current_version.version_id,
      };
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to deactivate template';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // GET /pdf-templates/{id}/versions - List all versions
  // ==========================================================================
  const getTemplateVersions = async (
    templateId: number
  ): Promise<GetTemplateVersionsResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate template exists
      const template = allMockTemplates.find((t) => t.id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      return mockTemplateVersions;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch template versions';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // GET /pdf-templates/{id}/versions/{version_id} - Get version detail
  // ==========================================================================
  const getTemplateVersionDetail = async (
    templateId: number,
    versionId: number
  ): Promise<GetTemplateVersionDetailResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate template exists
      const template = allMockTemplates.find((t) => t.id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }

      // Validate version exists (mock check)
      if (versionId < 1 || versionId > 10) {
        throw new Error('Version not found');
      }

      return mockTemplateVersionDetail;
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'Failed to fetch version details';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // POST /pdf-templates/simulate - Simulate full ETO process
  // ==========================================================================
  const simulateTemplate = async (
    request: PostTemplateSimulateRequest
  ): Promise<PostTemplateSimulateResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate required fields
      if (!request.pdf_file_id) {
        throw new Error('PDF file ID is required');
      }

      if (request.signature_objects.length < 1) {
        throw new Error('At least one signature object is required');
      }

      if (request.extraction_fields.length < 1) {
        throw new Error('At least one extraction field is required');
      }

      // Return mock simulation response
      return mockSimulateResponse;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to simulate template';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return {
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

    // State
    isLoading,
    error,
  };
}
