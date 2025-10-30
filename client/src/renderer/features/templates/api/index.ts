/**
 * Templates API
 * Exports all API hooks and types
 */

// Export all hooks
export {
  useTemplates,
  useTemplateDetail,
  useTemplateVersionDetail,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
  useActivateTemplate,
  useDeactivateTemplate,
  useSimulateTemplate,
} from './hooks';

// Export API types
export type {
  GetTemplatesQueryParams,
  GetTemplatesResponse,
  GetTemplateDetailResponse,
  PostTemplateCreateRequest,
  PostTemplateCreateResponse,
  PutTemplateUpdateRequest,
  PutTemplateUpdateResponse,
  PostTemplateActivateResponse,
  PostTemplateDeactivateResponse,
  GetTemplateVersionDetailResponse,
  PostTemplateSimulateRequest,
  PostTemplateSimulateResponse,
  ExtractedFieldResult,
  ExecutionStepResult,
} from './types';
