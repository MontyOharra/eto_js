/**
 * ETO Runs Feature
 * Public API for ETO run management and monitoring
 */

// ============================================================================
// Domain Types
// ============================================================================

export type {
  // Status and processing types
  EtoRunStatus,
  EtoProcessingStep,
  EtoSourceType,

  // Domain entities
  EtoSource,
  EtoPdfInfo,
  EtoMatchedTemplate,
  EtoRunListItem,
  EtoRunDetail,

  // Stage types
  EtoStageTemplateMatching,
  EtoStageDataExtraction,
  EtoStagePipelineExecution,
  EtoPipelineExecutionStep,

  // Extraction types
  ExtractionResult,
  ExtractedFieldWithBox,
} from './types';

// ============================================================================
// API Types
// ============================================================================

export type {
  GetEtoRunsQueryParams,
  GetEtoRunsResponse,
  GetEtoRunDetailResponse,
  PostEtoRunUploadResponse,
  PostEtoRunsReprocessRequest,
  PostEtoRunsSkipRequest,
  DeleteEtoRunsRequest,
} from './api/types';

// ============================================================================
// API Hooks
// ============================================================================

export {
  useEtoRuns,
  useEtoRunDetail,
  useCreateEtoRun,
  useReprocessRuns,
  useSkipRuns,
  useDeleteRuns,
  getPdfDownloadUrl,
} from './api/hooks';

// ============================================================================
// Non-API Hooks
// ============================================================================

export { useEtoEvents } from './hooks';

// ============================================================================
// Components
// ============================================================================

export * from './components';
