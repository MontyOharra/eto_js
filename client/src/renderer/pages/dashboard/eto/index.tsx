import { createFileRoute } from '@tanstack/react-router';
import { useMemo, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  useEtoRuns,
  useCreateEtoRun,
  useReprocessRuns,
  useSkipRuns,
  useDeleteRuns,
  useEtoEvents,
  EtoRunTable,
  EtoRunDetail,
  type EtoRunListItem,
  type EtoRunStatus,
} from '../../../features/eto';
import { TemplateBuilderModal } from '../../../features/templates/components';
import { useCreateTemplate, useActivateTemplate } from '../../../features/templates';

export const Route = createFileRoute('/dashboard/eto/')({
  component: EtoPage,
});

function EtoPage() {
  // TanStack Query client for cache invalidation
  const queryClient = useQueryClient();

  // TanStack Query hooks
  const { data: etoRunsData, isLoading, error } = useEtoRuns();
  const createEtoRun = useCreateEtoRun();
  const reprocessMutation = useReprocessRuns();
  const skipMutation = useSkipRuns();
  const deleteMutation = useDeleteRuns();
  const createTemplate = useCreateTemplate();
  const activateTemplate = useActivateTemplate();

  // State for run detail modal
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // State for template builder modal
  const [templateBuilderPdfId, setTemplateBuilderPdfId] = useState<number | null>(null);
  const [templateBuilderRunId, setTemplateBuilderRunId] = useState<number | null>(null);

  // SSE connection status
  const [isLiveConnected, setIsLiveConnected] = useState(false);

  // Derive grouped runs from query data
  const runsByStatus = useMemo(() => {
    const grouped: Record<EtoRunStatus, EtoRunListItem[]> = {
      not_started: [],
      processing: [],
      success: [],
      failure: [],
      needs_template: [],
      skipped: [],
    };

    if (etoRunsData?.items) {
      etoRunsData.items.forEach((run) => {
        grouped[run.status].push(run);
      });
    }

    return grouped;
  }, [etoRunsData]);

  // ==========================================================================
  // Real-time Event Handlers (SSE)
  // ==========================================================================
  // SSE events from background worker require manual query invalidation to trigger refetch.
  // Unlike mutations (which auto-invalidate), SSE events come from external processing,
  // so we must explicitly tell TanStack Query to refetch the updated data.

  const handleRunCreated = useCallback((data: any) => {
    console.log('[ETO] New run created via SSE:', data.id);
    // Invalidate queries to trigger refetch with new run
    queryClient.invalidateQueries({ queryKey: ['eto-runs'] });
  }, [queryClient]);

  const handleRunUpdated = useCallback((data: any) => {
    console.log('[ETO] Run updated via SSE:', data);
    // Invalidate queries to trigger refetch with updated status
    queryClient.invalidateQueries({ queryKey: ['eto-runs'] });
    if (data.id) {
      queryClient.invalidateQueries({ queryKey: ['eto-run', data.id] });
    }
  }, [queryClient]);

  const handleRunDeleted = useCallback((runId: number) => {
    console.log('[ETO] Run deleted via SSE:', runId);
    // Invalidate queries to trigger refetch without deleted run
    queryClient.invalidateQueries({ queryKey: ['eto-runs'] });
  }, [queryClient]);

  // Connect to SSE stream for real-time updates
  useEtoEvents({
    onRunCreated: handleRunCreated,
    onRunUpdated: handleRunUpdated,
    onRunDeleted: handleRunDeleted,
    onConnected: () => setIsLiveConnected(true),
    onDisconnected: () => setIsLiveConnected(false),
  });

  // ==========================================================================
  // Button Handlers
  // ==========================================================================

  const handleView = (runId: number) => {
    setSelectedRunId(runId);
  };

  const handleSkip = async (runId: number) => {
    try {
      await skipMutation.mutateAsync({ run_ids: [runId] });
      // TanStack Query auto-invalidates and refetches on success
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
      setTemplateBuilderRunId(runId); // Track run ID for reprocessing after save
    } else {
      console.error('Run not found:', runId);
    }
  };

  const handleReprocess = async (runId: number) => {
    try {
      await reprocessMutation.mutateAsync({ run_ids: [runId] });
      // TanStack Query auto-invalidates and refetches on success
    } catch (err) {
      console.error('Failed to reprocess run:', err);
    }
  };

  const handleDelete = async (runId: number) => {
    try {
      await deleteMutation.mutateAsync({ run_ids: [runId] });
      // TanStack Query auto-invalidates and refetches on success
    } catch (err) {
      console.error('Failed to delete run:', err);
    }
  };

  const handleSaveTemplate = async (templateData: any) => {
    console.log('Saving template:', templateData);

    try {
      // Call API to save template
      const createdTemplate = await createTemplate.mutateAsync({
        name: templateData.name,
        description: templateData.description,
        source_pdf_id: templateData.source_pdf_id!,
        signature_objects: templateData.signature_objects,
        extraction_fields: templateData.extraction_fields,
        pipeline_state: templateData.pipeline_state,
        visual_state: templateData.visual_state,
      } as any);

      console.log('Template created successfully:', createdTemplate.id);

      // Automatically activate the template
      await activateTemplate.mutateAsync(createdTemplate.id);
      console.log('Template activated successfully');

      // Reprocess the ETO run if it was built from a run
      if (templateBuilderRunId) {
        console.log('Reprocessing ETO run:', templateBuilderRunId);
        await reprocessMutation.mutateAsync({ run_ids: [templateBuilderRunId] });
        console.log('ETO run reprocessed successfully');
      }

      // Close modal
      setTemplateBuilderPdfId(null);
      setTemplateBuilderRunId(null);

      // TanStack Query will auto-refetch when mutations complete
    } catch (err) {
      console.error('Failed to create/activate template:', err);
      // Re-throw to let modal handle error display
      throw err;
    }
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
          await createEtoRun.mutateAsync(file);
          // TanStack Query auto-invalidates and refetches on success
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
          <p className="text-red-200">
            {error instanceof Error ? error.message : 'Failed to load ETO runs'}
          </p>
          <button
            onClick={() => window.location.reload()}
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
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-white">ETO Runs</h1>
            {/* Real-time connection status */}
            <div className="flex items-center gap-2 text-sm">
              {isLiveConnected ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                  </span>
                  <span className="text-green-400 font-medium">Live</span>
                </>
              ) : (
                <>
                  <span className="inline-flex h-2 w-2 rounded-full bg-yellow-500"></span>
                  <span className="text-yellow-400 font-medium">Connecting...</span>
                </>
              )}
            </div>
          </div>
          <p className="text-gray-400 mt-2">
            Monitor and manage extraction, transformation, and orchestration runs
          </p>
        </div>
        <button
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleManualUpload}
          disabled={isLoading || createEtoRun.isPending}
        >
          {createEtoRun.isPending ? 'Uploading...' : '+ Upload PDF'}
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
        <EtoRunTable
          title="Successful"
          status="success"
          runs={runsByStatus.success}
          onView={handleView}
        />

        {/* Failed Runs */}
        <EtoRunTable
          title="Failed"
          status="failure"
          runs={runsByStatus.failure}
          onView={handleView}
          onReprocess={handleReprocess}
          onSkip={handleSkip}
          onBulkSkip={async (runIds) => {
            await skipMutation.mutateAsync({ run_ids: runIds });
          }}
          onBulkReprocess={async (runIds) => {
            await reprocessMutation.mutateAsync({ run_ids: runIds });
          }}
        />

        {/* Needs Template Runs */}
        <EtoRunTable
          title="Needs Template"
          status="needs_template"
          runs={runsByStatus.needs_template}
          onBuildTemplate={handleBuildTemplate}
          onReprocess={handleReprocess}
          onSkip={handleSkip}
          onBulkSkip={async (runIds) => {
            await skipMutation.mutateAsync({ run_ids: runIds });
          }}
          onBulkReprocess={async (runIds) => {
            await reprocessMutation.mutateAsync({ run_ids: runIds });
          }}
        />
        {/* Processing Runs */}
        <EtoRunTable
          title="Processing"
          status="processing"
          runs={runsByStatus.processing}
        />
        {/* Skipped Runs */}
        <EtoRunTable
          title="Skipped"
          status="skipped"
          runs={runsByStatus.skipped}
          onReprocess={handleReprocess}
          onDelete={handleDelete}
          onBulkReprocess={async (runIds) => {
            await reprocessMutation.mutateAsync({ run_ids: runIds });
          }}
          onBulkDelete={async (runIds) => {
            await deleteMutation.mutateAsync({ run_ids: runIds });
          }}
        />
        {/* Not Started Runs */}
        <EtoRunTable
          title="Not Started"
          status="not_started"
          runs={runsByStatus.not_started}
        />
      </div>

      {/* Run Detail Modal */}
      <EtoRunDetail
        isOpen={selectedRunId !== null}
        runId={selectedRunId}
        onClose={() => setSelectedRunId(null)}
      />

      {/* Template Builder Modal */}
      <TemplateBuilderModal
        isOpen={templateBuilderPdfId !== null}
        mode="create"
        pdfFileId={templateBuilderPdfId}
        pdfFile={null}
        onClose={() => {
          setTemplateBuilderPdfId(null);
          setTemplateBuilderRunId(null);
        }}
        onSave={handleSaveTemplate}
      />
    </div>
  );
}
