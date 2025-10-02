import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { pipelineApiClient } from "../../services/api";

export const Route = createFileRoute("/transformation_pipeline/view-pipeline/$pipelineId")({
  component: PipelineViewPage,
});

function PipelineViewPage() {
  const { pipelineId } = Route.useParams();
  const [pipeline, setPipeline] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPipeline = async () => {
      try {
        setLoading(true);
        setError(null);
        const fetchedPipeline = await pipelineApiClient.getPipeline(pipelineId);
        setPipeline(fetchedPipeline);
        console.log('Fetched pipeline data:', JSON.stringify(fetchedPipeline, null, 2));
      } catch (err: any) {
        console.error('Failed to fetch pipeline:', err);
        setError(err.message || 'Failed to load pipeline');
      } finally {
        setLoading(false);
      }
    };

    fetchPipeline();
  }, [pipelineId]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-400">Loading pipeline...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-900 rounded-full mb-4">
            <svg className="h-8 w-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-300 mb-2">Failed to load pipeline</h3>
          <p className="text-gray-500 mb-6 max-w-md mx-auto">{error}</p>
          <Link
            to="/transformation_pipeline"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Back to Pipelines
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Pipeline Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">{pipeline?.name}</h1>
            <p className="mt-1 text-sm text-gray-400">
              {pipeline?.description || 'No description'} • ID: {pipeline?.id}
            </p>
          </div>
          <div className="flex items-center space-x-3">
            {pipeline?.is_active ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Active
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                Inactive
              </span>
            )}
            <span className="text-sm text-gray-400">(View Only)</span>
          </div>
        </div>

        {/* Pipeline Stats */}
        <div className="flex items-center space-x-6 mt-3 text-sm text-gray-400">
          <span>{pipeline?.module_count || 0} modules</span>
          <span>{pipeline?.connection_count || 0} connections</span>
          <span>{pipeline?.entry_point_count || 0} entry points</span>
          <span>Created: {new Date(pipeline?.created_at).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Raw Data Display */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pipeline JSON */}
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700">
              <h3 className="text-lg font-medium text-white">Pipeline JSON</h3>
              <p className="text-sm text-gray-400">Execution state and module configuration</p>
            </div>
            <div className="p-4">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto bg-gray-900 p-4 rounded border border-gray-600 max-h-96 overflow-y-auto">
                {JSON.stringify(pipeline?.pipeline_json, null, 2)}
              </pre>
            </div>
          </div>

          {/* Visual JSON */}
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            <div className="px-4 py-3 border-b border-gray-700">
              <h3 className="text-lg font-medium text-white">Visual JSON</h3>
              <p className="text-sm text-gray-400">UI positioning and layout data</p>
            </div>
            <div className="p-4">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto bg-gray-900 p-4 rounded border border-gray-600 max-h-96 overflow-y-auto">
                {JSON.stringify(pipeline?.visual_json, null, 2)}
              </pre>
            </div>
          </div>

          {/* Pipeline Metadata */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 lg:col-span-2">
            <div className="px-4 py-3 border-b border-gray-700">
              <h3 className="text-lg font-medium text-white">Pipeline Metadata</h3>
              <p className="text-sm text-gray-400">System information and timestamps</p>
            </div>
            <div className="p-4">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto bg-gray-900 p-4 rounded border border-gray-600">
                {JSON.stringify({
                  id: pipeline?.id,
                  name: pipeline?.name,
                  description: pipeline?.description,
                  is_active: pipeline?.is_active,
                  module_count: pipeline?.module_count,
                  connection_count: pipeline?.connection_count,
                  entry_point_count: pipeline?.entry_point_count,
                  plan_checksum: pipeline?.plan_checksum,
                  compiled_at: pipeline?.compiled_at,
                  created_at: pipeline?.created_at
                }, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}