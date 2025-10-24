import { createFileRoute, Link } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { usePipelinesApi } from '../../../features/pipelines/hooks/usePipelinesApi';
import { PipelineCard } from '../../../features/pipelines/components';
import { TestExecutedPipelineModal } from '../../../features/pipelines/components/TestExecutedPipelineModal';
import { PipelineListItem } from '../../../features/pipelines/types';

export const Route = createFileRoute('/dashboard/pipelines/')({
  component: PipelinesPage,
});

type SortBy = 'id' | 'created_at' | 'updated_at';
type SortOrder = 'asc' | 'desc';

function PipelinesPage() {
  const {
    getPipelines,
    isLoading,
    error,
  } = usePipelinesApi();

  const [allPipelines, setAllPipelines] = useState<PipelineListItem[]>([]);
  const [sortBy, setSortBy] = useState<SortBy>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);

  // Fetch pipelines on mount
  useEffect(() => {
    loadPipelines();
  }, []);

  const loadPipelines = async () => {
    try {
      const response = await getPipelines();
      setAllPipelines(response.items);
    } catch (err) {
      console.error('Failed to load pipelines:', err);
    }
  };

  // Sort pipelines
  const getSortedPipelines = (): PipelineListItem[] => {
    const sorted = [...allPipelines].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortBy) {
        case 'id':
          aValue = a.id;
          bValue = b.id;
          break;
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'updated_at':
          aValue = new Date(a.updated_at).getTime();
          bValue = new Date(b.updated_at).getTime();
          break;
        default:
          aValue = a.id;
          bValue = b.id;
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return sorted;
  };

  const sortedPipelines = getSortedPipelines();

  // ==========================================================================
  // Button Handlers
  // ==========================================================================

  const handleView = (pipelineId: number) => {
    console.log('View pipeline:', pipelineId);
    // TODO: Navigate to pipeline detail page or open modal
    // navigate({ to: `/dashboard/pipelines/${pipelineId}` });
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
            onClick={loadPipelines}
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
          <h1 className="text-3xl font-bold text-white">Transformation Pipelines</h1>
          <p className="text-gray-400 mt-2">
            Development/Testing tool for pipeline creation - In production, pipelines are embedded in templates
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsTestModalOpen(true)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors font-medium"
          >
            Test Executed Pipeline View
          </button>
          <Link
            to="/dashboard/pipelines/create"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
          >
            + Create Pipeline
          </Link>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="mb-6 bg-blue-900 border border-blue-700 rounded-lg p-4">
          <p className="text-blue-200">Loading pipelines...</p>
        </div>
      )}

      {/* Sort Controls */}
      <div className="mb-6 bg-gray-800 border border-gray-700 rounded-lg p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Sort By */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-300">
              Sort by:
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortBy)}
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="id">Pipeline ID</option>
              <option value="created_at">Created Date</option>
              <option value="updated_at">Updated Date</option>
            </select>
          </div>

          {/* Sort Order */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-300">Order:</label>
            <button
              onClick={() =>
                setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
              }
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 hover:bg-gray-600 transition-colors flex items-center space-x-1"
            >
              <span>{sortOrder === 'asc' ? 'Ascending' : 'Descending'}</span>
              <svg
                className={`w-4 h-4 transition-transform ${sortOrder === 'desc' ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 15l7-7 7 7"
                />
              </svg>
            </button>
          </div>

          {/* Results Count */}
          <div className="ml-auto text-sm text-gray-400">
            {sortedPipelines.length} pipeline
            {sortedPipelines.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Pipelines Display */}
      <div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedPipelines.map((pipeline) => (
            <PipelineCard
              key={pipeline.id}
              pipeline={pipeline}
              onView={handleView}
            />
          ))}
        </div>

      {/* Empty State */}
      {sortedPipelines.length === 0 && !isLoading && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-400 mb-4">
            <svg
              className="mx-auto h-12 w-12 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-white mb-2">
            No pipelines yet
          </h3>
          <p className="text-gray-400 mb-4">
            Get started by creating your first transformation pipeline for testing
          </p>
          <Link
            to="/dashboard/pipelines/create"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
          >
            Create Pipeline
          </Link>
        </div>
      )}
    </div>

      {/* Test Modal */}
      <TestExecutedPipelineModal
        isOpen={isTestModalOpen}
        onClose={() => setIsTestModalOpen(false)}
      />
    </div>
  );
}
