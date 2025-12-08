import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useState, useEffect, useRef } from 'react';
import {
  EtoRunDetailHeader,
  EtoRunDetailOverview,
  MatchedSubRunsSection,
  NeedsTemplateSection,
  SkippedSubRunsSection,
  EtoRunDetailSidebar,
  EtoSubRunDetailModal,
  useEtoRunDetail,
  useReprocessSubRun,
  useSkipSubRun,
  useReprocessRun,
  useSkipRun,
  useDeleteRuns,
  useUpdateEtoRun,
  EtoRunDetail,
} from '../../../features/eto';
import { TemplateBuilder, TemplateBuilderData } from '../../../features/templates/components/TemplateBuilder';
import { useCreateTemplate, useActivateTemplate, CreateTemplateRequest } from '../../../features/templates';
import { createSubsetPdf, useUploadPdf, getPdfDownloadUrl, PdfViewerModal } from '../../../features/pdf';

export const Route = createFileRoute('/dashboard/eto/$runId')({
  component: EtoRunDetailPage,
});

/**
 * Format milliseconds to human-readable duration
 */
function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}

/**
 * Format file size in bytes to human-readable string
 */
function formatFileSize(bytes: number | null): string {
  if (bytes === null) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Get display string for source type
 */
function getSourceDisplay(detail: EtoRunDetail): string {
  if (detail.source.type === 'email') {
    return `Email from ${detail.source.sender_email}`;
  }
  return 'Manual Upload';
}

/**
 * Get timestamp for source (received_at for email, created_at for manual)
 */
function getSourceDate(detail: EtoRunDetail): string {
  if (detail.source.type === 'email') {
    return detail.source.received_at;
  }
  return detail.source.created_at;
}

function EtoRunDetailPage() {
  const { runId } = Route.useParams();
  const navigate = useNavigate();

  // Note: SSE connection is established in parent EtoPage (eto/index.tsx)
  // No need for duplicate connection here

  // Modal state
  const [selectedSubRunId, setSelectedSubRunId] = useState<number | null>(null);

  // Fetch run detail from API
  const { data: detail, isLoading, isError, error } = useEtoRunDetail(parseInt(runId));

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

  // Template builder modal state
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [builderPdfFile, setBuilderPdfFile] = useState<File | null>(null);
  const [isPreparingPdf, setIsPreparingPdf] = useState(false);
  const [builderKey, setBuilderKey] = useState(0);

  // PDF Viewer modal state
  const [isPdfViewerOpen, setIsPdfViewerOpen] = useState(false);

  // Handler for opening sub-run detail modal
  const handleViewSubRunDetails = (subRunId: number) => {
    setSelectedSubRunId(subRunId);
  };

  // Handlers for sub-run operations
  const handleReprocessSubRun = (subRunId: number) => {
    reprocessSubRun.mutate(subRunId);
  };

  const handleSkipSubRun = (subRunId: number) => {
    skipSubRun.mutate(subRunId);
  };

  // Handlers for run-level operations
  const handleReprocessAll = () => {
    reprocessRun.mutate(parseInt(runId));
  };

  const handleSkipAll = () => {
    skipRun.mutate(parseInt(runId));
  };

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this run? This action cannot be undone.')) {
      deleteRuns.mutate({ run_ids: [parseInt(runId)] }, {
        onSuccess: () => {
          navigate({ to: '/dashboard/eto' });
        },
      });
    }
  };

  const handleViewPdf = () => {
    setIsPdfViewerOpen(true);
  };

  // Handler for building a template from a sub-run's pages
  const handleBuildTemplate = async (subRunId: number) => {
    if (!detail) return;

    // Find the sub-run to get its matched pages
    const subRun = detail.sub_runs.find(sr => sr.id === subRunId);
    if (!subRun || subRun.matched_pages.length === 0) {
      console.error('[handleBuildTemplate] Sub-run not found or has no matched pages');
      return;
    }

    setIsPreparingPdf(true);

    try {
      // Download the PDF from backend
      const pdfUrl = getPdfDownloadUrl(detail.pdf.id);
      const response = await fetch(pdfUrl);
      if (!response.ok) {
        throw new Error(`Failed to download PDF: ${response.statusText}`);
      }

      const pdfBlob = await response.blob();
      const pdfFile = new File([pdfBlob], detail.pdf.original_filename, {
        type: 'application/pdf',
      });

      // Convert matched_pages from 1-indexed to 0-indexed for createSubsetPdf
      const zeroIndexedPages = subRun.matched_pages.map(p => p - 1);

      // Create subset PDF with only the matched pages
      const subsetPdfFile = await createSubsetPdf(pdfFile, zeroIndexedPages);

      // Open the template builder with the subset PDF
      setBuilderPdfFile(subsetPdfFile);
      setBuilderKey(prev => prev + 1);
      setIsBuilderOpen(true);
    } catch (err) {
      console.error('[handleBuildTemplate] Failed to prepare PDF:', err);
      alert(`Failed to prepare PDF for template builder: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsPreparingPdf(false);
    }
  };

  // Handler for closing the template builder
  const handleCloseBuilder = () => {
    setIsBuilderOpen(false);
    setBuilderPdfFile(null);
  };

  // Handler for saving a template from the builder
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
  const sourceDisplay = getSourceDisplay(detail);
  const sourceDate = getSourceDate(detail);
  const processingTime = detail.overview.processing_time_ms
    ? formatDuration(detail.overview.processing_time_ms)
    : '-';

  return (
    <div className="p-6 min-h-full overflow-auto">
      {/* Header with back button */}
      <EtoRunDetailHeader
        pdfFilename={detail.pdf.original_filename}
        onBack={() => navigate({ to: '/dashboard/eto' })}
      />

      <div className="grid grid-cols-4 gap-6">
        {/* Main content - 3 columns */}
        <div className="col-span-3 flex flex-col gap-6">
          {/* Overview Stats */}
          <EtoRunDetailOverview
            source={sourceDisplay}
            sourceDate={sourceDate}
            status={detail.status}
            totalPages={detail.pdf.page_count}
            templatesMatched={detail.overview.templates_matched_count}
            processingTime={processingTime}
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
          sourceDate={sourceDate}
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
      <EtoSubRunDetailModal
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
