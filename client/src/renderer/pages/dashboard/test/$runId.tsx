import { createFileRoute, useNavigate } from '@tanstack/react-router';
import {
  EtoRunDetailHeader,
  EtoRunDetailOverview,
  MatchedSubRunsSection,
  NeedsTemplateSection,
  SkippedSubRunsSection,
  EtoRunDetailSidebar,
  getMockEtoRunDetailById,
} from '../../../features/test';

export const Route = createFileRoute('/dashboard/test/$runId')({
  component: EtoRunDetailPage,
});

function EtoRunDetailPage() {
  const { runId } = Route.useParams();
  const navigate = useNavigate();

  // Get mock data for this run ID
  const detail = getMockEtoRunDetailById(parseInt(runId));

  if (!detail) {
    return (
      <div className="p-6">
        <div className="text-white">Run not found</div>
      </div>
    );
  }

  const hasFailedRuns = detail.matchedSubRuns.some(sr => sr.status === 'failure');
  const hasNeedsTemplate = detail.needsTemplateSubRuns.length > 0;

  return (
    <div className="p-6">
      {/* Header with back button */}
      <EtoRunDetailHeader
        pdfFilename={detail.pdfFilename}
        onBack={() => navigate({ to: '/dashboard/test' })}
      />

      <div className="grid grid-cols-4 gap-6">
        {/* Main content - 3 columns */}
        <div className="col-span-3 flex flex-col gap-6">
          {/* Overview Stats */}
          <EtoRunDetailOverview
            source={detail.source}
            sourceDate={detail.sourceDate}
            masterStatus={detail.masterStatus}
            totalPages={detail.totalPages}
            templatesMatched={detail.matchedSubRuns.length}
            processingTime="16m 42s"
          />

          {/* Sub-runs Section - Matched Templates */}
          <MatchedSubRunsSection
            subRuns={detail.matchedSubRuns}
            onViewDetails={(subRunId) => {/* TODO: Implement view details */}}
            onReprocess={(subRunId) => {/* TODO: Implement reprocess */}}
            onSkip={(subRunId) => {/* TODO: Implement skip */}}
          />

          {/* Needs Template Section */}
          <NeedsTemplateSection
            subRuns={detail.needsTemplateSubRuns}
            onBuildTemplate={(subRunId) => {/* TODO: Implement build template */}}
            onReprocess={(subRunId) => {/* TODO: Implement reprocess */}}
            onSkip={(subRunId) => {/* TODO: Implement skip */}}
          />

          {/* Skipped Section */}
          <SkippedSubRunsSection
            subRuns={detail.skippedSubRuns}
            onReprocess={(subRunId) => {/* TODO: Implement reprocess */}}
          />
        </div>

        {/* Sidebar - 1 column */}
        <EtoRunDetailSidebar
          totalPages={detail.totalPages}
          fileSize={detail.pdfFile.fileSize}
          sourceDate={detail.sourceDate}
          hasFailedRuns={hasFailedRuns}
          hasNeedsTemplate={hasNeedsTemplate}
          matchedSubRuns={detail.matchedSubRuns}
          needsTemplateSubRuns={detail.needsTemplateSubRuns}
          skippedSubRuns={detail.skippedSubRuns}
          onViewPdf={() => {/* TODO: Implement view PDF */}}
          onReprocessAll={() => {/* TODO: Implement reprocess all */}}
          onSkipAll={() => {/* TODO: Implement skip all */}}
          onDelete={() => {/* TODO: Implement delete */}}
        />
      </div>
    </div>
  );
}
