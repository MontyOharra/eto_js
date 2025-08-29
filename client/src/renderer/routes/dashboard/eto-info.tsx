import { createFileRoute } from "@tanstack/react-router";
import { EtoRunsTable } from "../../components/EtoRunsTable";
import { TemplateBuilderModal } from "../../components/TemplateBuilderModal";
import { ConfirmationModal } from "../../components/ConfirmationModal";
import { ExtractionResultViewerModal } from "../../components/ExtractionResultViewerModal";
import { useEtoRuns, useServerHealth } from "../../hooks/useApi";
import { useMemo, useState } from "react";

export const Route = createFileRoute("/dashboard/eto-info")({
  component: EtoInfoPage,
});

function EtoInfoPage() {
  // Fetch real data from API
  const { data: allRuns, loading, error, refetch } = useEtoRuns({ 
    limit: 100, 
    autoRefresh: true, 
    refreshInterval: 15000 
  });
  const { isServerOnline } = useServerHealth();

  // Modal state for template builder
  const [buildingTemplateForRun, setBuildingTemplateForRun] = useState<string | null>(null);
  const [viewingExtractionForRun, setViewingExtractionForRun] = useState<string | null>(null);
  
  // Confirmation modal state
  const [confirmationModal, setConfirmationModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  } | null>(null);

  // Group runs by status
  const { successRuns, failureRuns, needsTemplateRuns, processingRuns, skippedRuns } = useMemo(() => {
    if (!allRuns) {
      return {
        successRuns: [],
        failureRuns: [],
        needsTemplateRuns: [],
        processingRuns: [],
        skippedRuns: [],
      };
    }

    return {
      successRuns: allRuns.filter(run => run.status === "success"),
      failureRuns: allRuns.filter(run => run.status === "failure"), 
      needsTemplateRuns: allRuns.filter(run => run.status === "needs_template"),
      // Combine both processing and not_started into a single processing group
      processingRuns: allRuns.filter(run => run.status === "processing" || run.status === "not_started"),
      skippedRuns: allRuns.filter(run => run.status === "skipped"),
    };
  }, [allRuns]);

  const handleReview = (runId: string) => {
    console.log("Build Template for run:", runId);
    setBuildingTemplateForRun(runId);
  };

  const handleTemplateBuilderSave = (templateData: any) => {
    console.log("Template saved successfully:", templateData);
    setBuildingTemplateForRun(null);
  };

  const handleTemplateBuilderClose = () => {
    setBuildingTemplateForRun(null);
  };

  const handleSkip = async (runId: string) => {
    try {
      const response = await fetch(`http://localhost:8080/api/eto-runs/${runId}/skip`, {
        method: 'POST',
      });
      
      if (response.ok) {
        // Refresh the data to show updated status
        refetch();
      } else {
        console.error('Failed to skip run:', await response.text());
      }
    } catch (error) {
      console.error('Error skipping run:', error);
    }
  };

  const handleView = (runId: string) => {
    console.log("View extraction results for run:", runId);
    setViewingExtractionForRun(runId);
  };

  const handleDelete = (runId: string) => {
    setConfirmationModal({
      isOpen: true,
      title: "Delete ETO Run",
      message: "Are you sure you want to permanently delete this ETO run? This action cannot be undone.",
      onConfirm: () => confirmDelete(runId)
    });
  };

  const confirmDelete = async (runId: string) => {
    try {
      const response = await fetch(`http://localhost:8080/api/eto-runs/${runId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        refetch(); // Refresh the data
        setConfirmationModal(null);
      } else {
        const errorData = await response.json();
        console.error('Failed to delete run:', errorData.error || 'Unknown error');
        setConfirmationModal(null);
      }
    } catch (error) {
      console.error('Error deleting run:', error);
      setConfirmationModal(null);
    }
  };

  const handleReprocess = async (runId: string) => {
    try {
      const response = await fetch(`http://localhost:8080/api/eto-runs/${runId}/reprocess`, {
        method: 'POST',
      });
      
      if (response.ok) {
        refetch(); // Refresh the data to show updated status
      } else {
        const errorData = await response.json();
        console.error('Failed to reprocess run:', errorData.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Error reprocessing run:', error);
    }
  };

  const closeConfirmationModal = () => {
    setConfirmationModal(null);
  };

  // Show loading state
  if (loading && !allRuns) {
    return (
      <div className="flex-1 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-blue-300 mb-2">
            ETO Information
          </h1>
          <p className="text-gray-400">
            Monitor and review PDF processing results
          </p>
        </div>
        
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading ETO runs...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error && !allRuns) {
    return (
      <div className="flex-1 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-blue-300 mb-2">
            ETO Information
          </h1>
          <p className="text-gray-400">
            Monitor and review PDF processing results
          </p>
        </div>
        
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6">
          <div className="flex items-center">
            <svg className="w-6 h-6 text-red-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-red-400 font-medium">Failed to load ETO runs</h3>
              <p className="text-gray-400 text-sm mt-1">{error}</p>
            </div>
          </div>
          <button 
            onClick={refetch}
            className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex-1 p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-blue-300 mb-2">
              ETO Information
            </h1>
            <p className="text-gray-400">
              Monitor and review PDF processing results
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Server status indicator */}
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${isServerOnline ? 'bg-green-400' : 'bg-red-400'}`}></div>
              <span className={`text-sm ${isServerOnline ? 'text-green-400' : 'text-red-400'}`}>
                {isServerOnline ? 'Server Online' : 'Server Offline'}
              </span>
            </div>
            
            {/* Refresh button */}
            <button 
              onClick={refetch}
              disabled={loading}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-sm rounded transition-colors"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
        
        {/* Data freshness indicator */}
        {allRuns && (
          <p className="text-xs text-gray-500 mt-2">
            Showing {allRuns.length} runs • Auto-refreshing every 15s
          </p>
        )}
      </div>

      <div className="space-y-6">
        <EtoRunsTable
          title="Currently Processing"
          runs={processingRuns}
          status="processing"
          showButtons={false}
        />

        <EtoRunsTable
          title="Successful Extractions"
          runs={successRuns}
          status="success"
          onView={handleView}
        />

        <EtoRunsTable
          title="Failed Extractions"
          runs={failureRuns}
          status="failure"
          onView={handleView}
          onReview={handleReview}
          onSkip={handleSkip}
        />

        <EtoRunsTable
          title="Needs Template Creation"
          runs={needsTemplateRuns}
          status="needs_template"
          onReview={handleReview}
          onSkip={handleSkip}
        />

        <EtoRunsTable
          title="Skipped Runs"
          runs={skippedRuns}
          status="skipped"
          onDelete={handleDelete}
          onReprocess={handleReprocess}
        />
      </div>
      </div>
      
      {/* Template Builder Modal */}
      <TemplateBuilderModal
        runId={buildingTemplateForRun}
        onClose={handleTemplateBuilderClose}
        onSave={handleTemplateBuilderSave}
      />

      {/* Extraction Results Viewer Modal */}
      <ExtractionResultViewerModal
        runId={viewingExtractionForRun}
        onClose={() => setViewingExtractionForRun(null)}
      />
      
      {/* Confirmation Modal */}
      {confirmationModal && (
        <ConfirmationModal
          isOpen={confirmationModal.isOpen}
          title={confirmationModal.title}
          message={confirmationModal.message}
          variant="danger"
          confirmText="Delete"
          onConfirm={confirmationModal.onConfirm}
          onCancel={closeConfirmationModal}
        />
      )}
    </>
  );
}
