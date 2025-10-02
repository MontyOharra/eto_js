import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { pipelineApiClient } from "../../services/api";

export const Route = createFileRoute("/transformation_pipeline/")({
  component: PipelineListPage,
});

// Icon Components (inline SVGs)
const PlusIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
);

const DocumentDuplicateIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M7 9V2a2 2 0 012-2h10a2 2 0 012 2v12a2 2 0 01-2 2h-3v5a2 2 0 01-2 2H4a2 2 0 01-2-2V11a2 2 0 012-2h3zm2 0h5a2 2 0 012 2v8h3V2H9v7z" />
  </svg>
);

const ChartBarIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M18.375 2.25a.75.75 0 01.75.75v18a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM9.75 8.25a.75.75 0 01.75.75v12a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zM3 13.5a.75.75 0 01.75.75v6.75a.75.75 0 01-1.5 0v-6.75A.75.75 0 013 13.5zM14.25 4.5a.75.75 0 01.75.75v15.75a.75.75 0 01-1.5 0V5.25a.75.75 0 01.75-.75z" />
  </svg>
);

const ClockIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path fillRule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zM12.75 6a.75.75 0 00-1.5 0v6c0 .414.336.75.75.75h4.5a.75.75 0 000-1.5h-3.75V6z" clipRule="evenodd" />
  </svg>
);

function PipelineListPage() {
  const navigate = useNavigate();
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPipelines = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await pipelineApiClient.getPipelines({ summary_only: true });
        setPipelines(response.pipelines);
      } catch (err: any) {
        console.error('Failed to fetch pipelines:', err);
        setError(err.message || 'Failed to load pipelines');
      } finally {
        setLoading(false);
      }
    };

    fetchPipelines();
  }, []);

  return (
    <div className="min-h-full bg-gray-900">
      {/* Header Section */}
      <div className="bg-gray-800 shadow-lg border-b border-gray-700">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">Transformation Pipelines</h2>
              <p className="mt-1 text-sm text-gray-400">
                Create and manage data transformation pipelines for processing extracted data
              </p>
            </div>

            {/* Create New Pipeline Button */}
            <Link
              to="/transformation_pipeline/graph"
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Create Pipeline
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="px-6 py-6">
        {loading ? (
          /* Loading State */
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4"></div>
            <p className="text-gray-400">Loading pipelines...</p>
          </div>
        ) : error ? (
          /* Error State */
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-900 rounded-full mb-4">
              <svg className="h-8 w-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-300 mb-2">Failed to load pipelines</h3>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : pipelines.length === 0 ? (
          /* Empty State */
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-800 rounded-full mb-4">
              <DocumentDuplicateIcon className="h-8 w-8 text-gray-500" />
            </div>
            <h3 className="text-lg font-medium text-gray-300 mb-2">No pipelines yet</h3>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">
              Get started by creating your first transformation pipeline to process and transform your extracted data.
            </p>
            <Link
              to="/transformation_pipeline/graph"
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Create Your First Pipeline
            </Link>
          </div>
        ) : (
          /* Pipeline Grid */
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {pipelines.map((pipeline) => (
              <PipelineCard key={pipeline.id} pipeline={pipeline} />
            ))}
          </div>
        )}

        {/* Info Section */}
        <div className="mt-12 bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">About Transformation Pipelines</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex space-x-3">
              <div className="flex-shrink-0">
                <DocumentDuplicateIcon className="h-6 w-6 text-blue-400" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-300">Visual Pipeline Builder</h4>
                <p className="mt-1 text-sm text-gray-500">
                  Drag and drop modules to create complex data transformation workflows
                </p>
              </div>
            </div>
            <div className="flex space-x-3">
              <div className="flex-shrink-0">
                <ChartBarIcon className="h-6 w-6 text-green-400" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-300">Modular Components</h4>
                <p className="mt-1 text-sm text-gray-500">
                  Use pre-built modules or create custom ones for your specific needs
                </p>
              </div>
            </div>
            <div className="flex space-x-3">
              <div className="flex-shrink-0">
                <ClockIcon className="h-6 w-6 text-yellow-400" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-300">Real-time Processing</h4>
                <p className="mt-1 text-sm text-gray-500">
                  Execute pipelines on demand or integrate them into automated workflows
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Pipeline card component for displaying individual pipelines
function PipelineCard({ pipeline }: { pipeline: any }) {
  const navigate = useNavigate();

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleViewPipeline = () => {
    // Navigate to pipeline viewer using React Router
    navigate({ to: `/pipeline-view/${pipeline.id}` });
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-medium text-white truncate">{pipeline.name}</h3>
          {pipeline.description && (
            <p className="mt-1 text-sm text-gray-400 line-clamp-2">{pipeline.description}</p>
          )}
        </div>
        {pipeline.is_active ? (
          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            Active
          </span>
        ) : (
          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            Inactive
          </span>
        )}
      </div>

      {/* Pipeline Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4 text-center">
        <div>
          <div className="text-lg font-semibold text-white">{pipeline.module_count || 0}</div>
          <div className="text-xs text-gray-400">Modules</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-white">{pipeline.connection_count || 0}</div>
          <div className="text-xs text-gray-400">Connections</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-white">{pipeline.entry_point_count || 0}</div>
          <div className="text-xs text-gray-400">Entries</div>
        </div>
      </div>

      <div className="flex items-center text-sm text-gray-500 mb-4">
        <ClockIcon className="h-4 w-4 mr-1" />
        <span>Created: {formatDate(pipeline.created_at)}</span>
      </div>

      <div className="flex justify-end space-x-2">
        <button
          onClick={handleViewPipeline}
          className="px-3 py-1 text-sm text-gray-300 hover:text-white border border-gray-600 hover:border-gray-500 rounded-md transition-colors"
        >
          View
        </button>
        <button
          className="px-3 py-1 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
          onClick={() => alert('Run functionality coming soon!')}
        >
          Run
        </button>
      </div>
    </div>
  );
}