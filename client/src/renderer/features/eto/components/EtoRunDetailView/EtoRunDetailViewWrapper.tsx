import { useState, useEffect, useRef } from 'react';
import {
  EtoRunDetailHeader,
  EtoRunDetailOverview,
  MatchedSubRunsSection,
  NeedsTemplateSection,
  SkippedSubRunsSection,
  EtoRunDetailSidebar,
} from './index';
import { EtoSubRunDetailViewer } from '../EtoSubRunDetail/EtoSubRunDetailViewer';
import { TemplateBuilder, TemplateBuilderData } from '../../../templates/components/TemplateBuilder';
import { useCreateTemplate, useActivateTemplate, CreateTemplateRequest } from '../../../templates';
import { createSubsetPdf, useUploadPdf, getPdfDownloadUrl, PdfViewerModal } from '../../../pdf';
import {
  useEtoRunDetail,
  useReprocessSubRun,
  useSkipSubRun,
  useReprocessRun,
  useSkipRun,
  useDeleteRuns,
  useUpdateEtoRun,
} from '../../index';
import { apiClient } from '../../../../shared/api/client';
import { API_CONFIG } from '../../../../shared/api/config';
import type { ReprocessWarningsResponse } from '../../api/types';

interface EtoRunDetailViewWrapperProps {
  runId: number;
  onBack: () => void;
}

export function EtoRunDetailViewWrapper({ runId, onBack }: EtoRunDetailViewWrapperProps) {
  // Note: SSE connection is established at page level (eto/index.tsx)
  // No need for duplicate connection here

  // Modal state
  const [selectedSubRunId, setSelectedSubRunId] = useState<number | null>(null);

  // Fetch run detail from API
  const { data: detail, isLoading, isError, error } = useEtoRunDetail(runId);

  // Sub-run mutations
  const reprocessSubRun = useReprocessSubRun();
  const skipSubRun = useSkipSubRun();

  // Run-level mutations
  const reprocessRun = useReprocessRun();
  const skipRun = useSkipRun();
  const deleteRuns = useDeleteRuns();

  // Template builder mutations
  const { mutateAsync: uploadPdf } = useUploadPdf();
  const createTemplate = useCreateTemplate();
  const activateTemplate = useActivateTemplate();

  // Update run mutation (for marking as read)
  const updateRun = useUpdateEtoRun();

  // Track if we've already marked this run as read to avoid duplicate calls
  const hasMarkedAsRead = useRef(false);

  // Auto mark as read when viewing detail
  useEffect(() => {
    if (detail && !hasMarkedAsRead.current) {
      hasMarkedAsRead.current = true;
      updateRun.mutate({ runId: detail.id, updates: { is_read: true } });
    }
  }, [detail, updateRun]);

  // Reset hasMarkedAsRead when runId changes
  useEffect(() => {
    hasMarkedAsRead.current = false;
  }, [runId]);

  // Template builder modal state
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [builderPdfFile, setBuilderPdfFile] = useState<File | null>(null);
  const [isPreparingPdf, setIsPreparingPdf] = useState(false);
  const [builderKey, setBuilderKey] = useState(0); // Force re-mount template builder

  // PDF viewer state
  const [isPdfViewerOpen, setIsPdfViewerOpen] = useState(false);

  // Sub-run action handlers
  const handleViewSubRunDetails = (subRunId: number) => {
    setSelectedSubRunId(subRunId);
  };

  const handleReprocessSubRun = async (subRunId: number) => {
    try {
      // Check for warnings before reprocessing
      const response = await apiClient.get<ReprocessWarningsResponse>(
        `${API_CONFIG.ENDPOINTS.ETO_RUNS}/sub-runs/${subRunId}/reprocess-warnings`
      );
      const warnings = response.data;

      if (warnings.has_warnings && warnings.warning_message) {
        // Show confirmation dialog with warning
        const confirmed = confirm(
          `Warning: ${warnings.warning_message}\n\nAre you sure you want to reprocess this sub-run?`
        );
        if (!confirmed) {
          return;
        }
      }

      // Proceed with reprocessing
      reprocessSubRun.mutate(subRunId);
    } catch (error) {
      console.error('Failed to check reprocess warnings:', error);
      // If warning check fails, still allow reprocessing with generic confirmation
      const confirmed = confirm('Are you sure you want to reprocess this sub-run?');
      if (confirmed) {
        reprocessSubRun.mutate(subRunId);
      }
    }
  };

  const handleSkipSubRun = (subRunId: number) => {
    skipSubRun.mutate(subRunId);
  };

  // Run-level action handlers
  const handleReprocessAll = () => {
    if (!detail) return;
    reprocessRun.mutate(detail.id);
  };

  const handleSkipAll = () => {
    if (!detail) return;
    skipRun.mutate(detail.id);
  };

  const handleDelete = () => {
    if (!detail) return;
    if (confirm('Are you sure you want to delete this run? This action cannot be undone.')) {
      deleteRuns.mutate(
        { run_ids: [detail.id] },
        {
          onSuccess: () => {
            // After deletion, go back to list
            onBack();
          },
        }
      );
    }
  };

  const handleViewPdf = () => {
    setIsPdfViewerOpen(true);
  };

  // Template builder handlers
  const handleBuildTemplate = async (pageNumbers: number[]) => {
    if (!detail) return;

    setIsPreparingPdf(true);
    try {
      // Convert 1-indexed page numbers to 0-indexed indices for pdf-lib
      const pageIndices = pageNumbers.map(pageNum => pageNum - 1);

      // Download the original PDF
      const pdfUrl = getPdfDownloadUrl(detail.pdf.id);
      const response = await fetch(pdfUrl);
      if (!response.ok) {
        throw new Error(`Failed to download PDF: ${response.statusText}`);
      }
      const pdfBlob = await response.blob();

      // Create a subset PDF with the selected pages
      const subsetBlob = await createSubsetPdf(pdfBlob, pageIndices);

      // Convert to File object
      const pdfFile = new File([subsetBlob], `template_pages_${pageNumbers.join('_')}.pdf`, {
        type: 'application/pdf',
      });

      // Open template builder with the subset PDF
      setBuilderPdfFile(pdfFile);
      setBuilderKey(prev => prev + 1); // Force re-mount
      setIsBuilderOpen(true);
    } catch (err) {
      console.error('[handleBuildTemplate] Failed to prepare PDF:', err);
      alert(`Failed to prepare PDF for template builder: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsPreparingPdf(false);
    }
  };

  const handleCloseBuilder = () => {
    setIsBuilderOpen(false);
    setBuilderPdfFile(null);
  };

  const handleSaveTemplate = async (templateData: TemplateBuilderData) => {
    try {
      // Upload the PDF file
      const pdfToUpload = templateData.pdf_file || builderPdfFile;
      if (!pdfToUpload) {
        throw new Error('No PDF file available');
      }

      const uploadedPdf = await uploadPdf(pdfToUpload);
      if (!uploadedPdf.id) {
        throw new Error('PDF upload succeeded but returned no ID');
      }

      // Create the template
      const createRequest: CreateTemplateRequest = {
        name: templateData.name,
        description: templateData.description || '',
        customer_id: templateData.customer_id ?? undefined,
        is_autoskip: templateData.is_autoskip ?? false,
        source_pdf_id: uploadedPdf.id,
        signature_objects: templateData.signature_objects,
        extraction_fields: templateData.extraction_fields,
        pipeline_state: templateData.pipeline_state,
        visual_state: templateData.visual_state,
      };

      const createdTemplate = await createTemplate.mutateAsync(createRequest);

      // Immediately activate the template so it's used for matching
      await activateTemplate.mutateAsync(createdTemplate.id);

      // Close modal on success
      handleCloseBuilder();
    } catch (err) {
      console.error('[handleSaveTemplate] Failed to save template:', err);
      throw err; // Re-throw to let modal handle error
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-400">Loading run details...</div>
      </div>
    );
  }

  // Error state
  if (isError || !detail) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-red-400">
          {error?.message || 'Run not found'}
        </div>
      </div>
    );
  }

  // Filter sub-runs by status for each section
  const matchedSubRuns = detail.sub_runs.filter(
    sr => sr.status === 'success' || sr.status === 'failure'
  );
  const needsTemplateSubRuns = detail.sub_runs.filter(
    sr => sr.status === 'needs_template'
  );
  const skippedSubRuns = detail.sub_runs.filter(
    sr => sr.status === 'skipped'
  );

  // Compute derived values
  const hasFailedRuns = matchedSubRuns.some(sr => sr.status === 'failure');
  const hasNeedsTemplate = needsTemplateSubRuns.length > 0;

  return (
    <div className="p-6 h-full overflow-auto">
      {/* Header with back button */}
      <EtoRunDetailHeader
        pdfFilename={detail.pdf.original_filename}
        onBack={onBack}
      />

      <div className="grid grid-cols-4 gap-6">
        {/* Main content - 3 columns */}
        <div className="col-span-3 flex flex-col gap-6">
          {/* Overview Stats */}
          <EtoRunDetailOverview
            source={detail.source}
            status={detail.status}
          />

          {/* Sub-runs Section - Matched Templates */}
          <MatchedSubRunsSection
            subRuns={matchedSubRuns}
            onViewDetails={handleViewSubRunDetails}
            onReprocess={handleReprocessSubRun}
            onSkip={handleSkipSubRun}
          />

          {/* Needs Template Section */}
          <NeedsTemplateSection
            subRuns={needsTemplateSubRuns}
            onBuildTemplate={handleBuildTemplate}
            onReprocess={handleReprocessSubRun}
            onSkip={handleSkipSubRun}
          />

          {/* Skipped Section */}
          <SkippedSubRunsSection
            subRuns={skippedSubRuns}
            onReprocess={handleReprocessSubRun}
          />
        </div>

        {/* Sidebar - 1 column */}
        <EtoRunDetailSidebar
          pdf={detail.pdf}
          pageStatuses={detail.page_statuses}
          hasFailedRuns={hasFailedRuns}
          hasNeedsTemplate={hasNeedsTemplate}
          onViewPdf={handleViewPdf}
          onReprocessAll={handleReprocessAll}
          onSkipAll={handleSkipAll}
          onDelete={handleDelete}
        />
      </div>

      {/* Sub-run Detail Modal */}
      <EtoSubRunDetailViewer
        isOpen={selectedSubRunId !== null}
        subRunId={selectedSubRunId}
        onClose={() => setSelectedSubRunId(null)}
      />

      {/* Template Builder Modal */}
      <TemplateBuilder
        key={`builder-${builderKey}`}
        isOpen={isBuilderOpen}
        pdfFile={builderPdfFile}
        pdfFileId={null}
        pdfMetadata={null}
        onClose={handleCloseBuilder}
        onSave={handleSaveTemplate}
      />

      {/* PDF Viewer Modal */}
      <PdfViewerModal
        isOpen={isPdfViewerOpen}
        pdfId={detail?.pdf.id ?? null}
        filename={detail?.pdf.original_filename}
        onClose={() => setIsPdfViewerOpen(false)}
      />

      {/* Loading overlay when preparing PDF for template builder */}
      {isPreparingPdf && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
            <p className="text-white">Preparing PDF for template builder...</p>
          </div>
        </div>
      )}
    </div>
  );
}
