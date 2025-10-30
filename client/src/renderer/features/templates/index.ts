/**
 * Templates Feature
 * Unified exports for template operations
 */

// API hooks
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
} from './api';

// API types (Request/Response DTOs)
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
} from './api';

// Domain types
export type {
  TemplateStatus,
  PdfObjectType,
  BBox,
  TemplateVersionSummary,
  VersionListItem,
  PdfObjects,
  SignatureObject,
  ExtractionField,
  TemplateVersion,
  TemplateVersionDetail,
  TemplateListItem,
  TemplateDetail,
} from './types';
