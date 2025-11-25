import { createFileRoute, useNavigate } from '@tanstack/react-router';
import {
  EtoRunDetailHeader,
  EtoRunDetailOverview,
  MatchedSubRunsSection,
  NeedsTemplateSection,
  SkippedSubRunsSection,
  EtoRunDetailSidebar,
  useEtoRunDetail,
  useReprocessSubRun,
  useSkipSubRun,
  EtoRunDetail,
} from '../../../features/test';

export const Route = createFileRoute('/dashboard/test/$runId')({
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

  // Fetch run detail from API
  const { data: detail, isLoading, isError, error } = useEtoRunDetail(parseInt(runId));

  // Sub-run mutations
  const reprocessSubRun = useReprocessSubRun();
  const skipSubRun = useSkipSubRun();

  // Handlers for sub-run operations
  const handleReprocessSubRun = (subRunId: number) => {
    reprocessSubRun.mutate(subRunId);
  };

  const handleSkipSubRun = (subRunId: number) => {
    skipSubRun.mutate(subRunId);
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
    <div className="p-6">
      {/* Header with back button */}
      <EtoRunDetailHeader
        pdfFilename={detail.pdf.original_filename}
        onBack={() => navigate({ to: '/dashboard/test' })}
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
            onViewDetails={(subRunId) => {/* TODO: Implement view details */}}
            onReprocess={handleReprocessSubRun}
            onSkip={handleSkipSubRun}
          />

          {/* Needs Template Section */}
          <NeedsTemplateSection
            subRuns={needsTemplateSubRuns}
            onBuildTemplate={(subRunId) => {/* TODO: Implement build template */}}
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
          onViewPdf={() => {/* TODO: Implement view PDF */}}
          onReprocessAll={() => {/* TODO: Implement reprocess all */}}
          onSkipAll={() => {/* TODO: Implement skip all */}}
          onDelete={() => {/* TODO: Implement delete */}}
        />
      </div>
    </div>
  );
}
