import { createFileRoute } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { useMockEtoApi } from '../../../features/eto/hooks';
import { EtoRunsTable, RunDetailModal } from '../../../features/eto/components';
import { EtoRunListItem, EtoRunStatus } from '../../../features/eto/types';
import { TemplateBuilderModal } from '../../../features/templates/components';

export const Route = createFileRoute('/dashboard/eto/')({
  component: EtoPage,
});

function EtoPage() {
  const {
    getEtoRuns,
    uploadPdf,
    reprocessRuns,
    skipRuns,
    deleteRuns,
    isLoading,
    error,
  } = useMockEtoApi();

  // State to hold runs grouped by status
  const [runsByStatus, setRunsByStatus] = useState<
    Record<EtoRunStatus, EtoRunListItem[]>
  >({
    not_started: [],
    processing: [],
    success: [],
    failure: [],
    needs_template: [],
    skipped: [],
  });

  // State for run detail modal
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // State for template builder modal
  const [templateBuilderPdfId, setTemplateBuilderPdfId] = useState<number | null>(null);

  // Fetch runs on mount
  useEffect(() => {
    loadRuns();
  }, []);

  const loadRuns = async () => {
    try {
      const response = await getEtoRuns();

      // Group runs by status
      const grouped: Record<EtoRunStatus, EtoRunListItem[]> = {
        not_started: [],
        processing: [],
        success: [],
        failure: [],
        needs_template: [],
        skipped: [],
      };

      response.items.forEach((run) => {
        grouped[run.status].push(run);
      });

      setRunsByStatus(grouped);
    } catch (err) {
      console.error('Failed to load ETO runs:', err);
    }
  };

  // ==========================================================================
  // Button Handlers
  // ==========================================================================

  const handleView = (runId: number) => {
    setSelectedRunId(runId);
  };

  const handleReview = (runId: number) => {
    // Open detail modal - user can switch to Detail tab to review pipeline execution
    setSelectedRunId(runId);
  };

  const handleSkip = async (runId: number) => {
    try {
      await skipRuns({ run_ids: [runId] });
      // Reload runs after successful skip
      await loadRuns();
    } catch (err) {
      console.error('Failed to skip run:', err);
    }
  };

  const handleBuildTemplate = (runId: number) => {
    // Find the run and get its PDF ID
    const run = Object.values(runsByStatus)
      .flat()
      .find((r) => r.id === runId);

    if (run) {
      setTemplateBuilderPdfId(run.pdf.id);
    } else {
      console.error('Run not found:', runId);
    }
  };

  const handleReprocess = async (runId: number) => {
    try {
      await reprocessRuns({ run_ids: [runId] });
      // Reload runs after successful reprocess
      await loadRuns();
    } catch (err) {
      console.error('Failed to reprocess run:', err);
    }
  };

  const handleDelete = async (runId: number) => {
    try {
      await deleteRuns({ run_ids: [runId] });
      // Reload runs after successful delete
      await loadRuns();
    } catch (err) {
      console.error('Failed to delete run:', err);
    }
  };

  const handleSaveTemplate = async (templateData: any) => {
    console.log('Saving template:', templateData);
    // TODO: Call API to save template
    // await createTemplate(templateData);

    // Close modal
    setTemplateBuilderPdfId(null);

    // Reload runs to update status
    await loadRuns();
  };

  const handleManualUpload = () => {
    // Create a hidden file input element
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/pdf';

    input.onchange = async (e: Event) => {
      const target = e.target as HTMLInputElement;
      const file = target.files?.[0];

      if (file) {
        // Validate file type
        if (file.type !== 'application/pdf') {
          alert('Please select a PDF file');
          return;
        }

        try {
          // Upload PDF and create ETO run
          await uploadPdf(file);

          // Reload runs to show the new run
          await loadRuns();
        } catch (err) {
          console.error('Failed to upload PDF:', err);
          alert('Failed to upload PDF. Please try again.');
        }
      }
    };

    // Trigger the file picker
    input.click();
  };

  // ==========================================================================
  // Render
  // ==========================================================================

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-900 border border-red-700 rounded-lg p-4">
          <h2 className="text-xl font-bold text-red-300 mb-2">Error</h2>
          <p className="text-red-200">{error}</p>
          <button
            onClick={loadRuns}
            className="mt-4 px-4 py-2 bg-red-700 hover:bg-red-600 text-white rounded transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">ETO Runs</h1>
          <p className="text-gray-400 mt-2">
            Monitor and manage extraction, transformation, and orchestration runs
          </p>
        </div>
        <button
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
          onClick={handleManualUpload}
          disabled={isLoading}
        >
          + Upload PDF
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="mb-6 bg-blue-900 border border-blue-700 rounded-lg p-4">
          <p className="text-blue-200">Loading ETO runs...</p>
        </div>
      )}


      {/* Tables - One for each status */}
      <div className="space-y-4">
  
        {/* Success Runs */}
        <EtoRunsTable
          title="Successful"
          status="success"
          runs={runsByStatus.success}
          onView={handleView}
        />

        {/* Failed Runs */}
        <EtoRunsTable
          title="Failed"
          status="failure"
          runs={runsByStatus.failure}
          onView={handleView}
          onReview={handleReview}
          onSkip={handleSkip}
        />

        {/* Needs Template Runs */}
        <EtoRunsTable
          title="Needs Template"
          status="needs_template"
          runs={runsByStatus.needs_template}
          onBuildTemplate={handleBuildTemplate}
          onSkip={handleSkip}
        />
        {/* Processing Runs */}
        <EtoRunsTable
          title="Processing"
          status="processing"
          runs={runsByStatus.processing}
        />
        {/* Skipped Runs */}
        <EtoRunsTable
          title="Skipped"
          status="skipped"
          runs={runsByStatus.skipped}
          onReprocess={handleReprocess}
          onDelete={handleDelete}
        />
        {/* Not Started Runs */}
        <EtoRunsTable
          title="Not Started"
          status="not_started"
          runs={runsByStatus.not_started}
        />
      </div>

      {/* Run Detail Modal */}
      <RunDetailModal
        isOpen={selectedRunId !== null}
        runId={selectedRunId}
        onClose={() => setSelectedRunId(null)}
      />

      {/* Template Builder Modal */}
      <TemplateBuilderModal
        isOpen={templateBuilderPdfId !== null}
        pdfFileId={templateBuilderPdfId}
        pdfFile={null}
        onClose={() => setTemplateBuilderPdfId(null)}
        onSave={handleSaveTemplate}
      />
    </div>
  );
}
