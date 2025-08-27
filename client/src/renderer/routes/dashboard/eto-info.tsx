import { createFileRoute } from "@tanstack/react-router";
import { EtoRunsTable } from "../../components/EtoRunsTable";
import { EtoRunViewerModal } from "../../components/EtoRunViewerModal";
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

  // Modal state for PDF viewer
  const [viewingRunId, setViewingRunId] = useState<string | null>(null);

  // Group runs by status
  const { successRuns, failureRuns, unrecognizedRuns, errorRuns } = useMemo(() => {
    if (!allRuns) {
      return {
        successRuns: [],
        failureRuns: [],
        unrecognizedRuns: [],
        errorRuns: [],
      };
    }

    return {
      successRuns: allRuns.filter(run => run.status === "success"),
      failureRuns: allRuns.filter(run => run.status === "failure"),
      unrecognizedRuns: allRuns.filter(run => run.status === "unrecognized"),
      errorRuns: allRuns.filter(run => run.status === "error"),
    };
  }, [allRuns]);

  const handleView = (runId: string) => {
    console.log("View run:", runId);
    setViewingRunId(runId);
  };

  const handleReview = (runId: string) => {
    console.log("Build Template for run:", runId);
    // TODO: Open template building interface
    setViewingRunId(runId);
  };

  const handleCloseViewer = () => {
    setViewingRunId(null);
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
          title="Successful Extractions"
          runs={successRuns}
          status="success"
          onView={handleView}
          onReview={handleReview}
        />

        <EtoRunsTable
          title="Failed Extractions"
          runs={failureRuns}
          status="failure"
          onView={handleView}
          onReview={handleReview}
        />

        <EtoRunsTable
          title="Processing Errors"
          runs={errorRuns}
          status="error"
          onView={handleView}
          onReview={handleReview}
        />

        <EtoRunsTable
          title="Unrecognized Attachments"
          runs={unrecognizedRuns}
          status="unrecognized"
          onView={handleView}
          onReview={handleReview}
        />
      </div>

      {/* PDF Viewer Modal */}
      <EtoRunViewerModal 
        runId={viewingRunId}
        onClose={handleCloseViewer}
      />
    </div>
  );
}
