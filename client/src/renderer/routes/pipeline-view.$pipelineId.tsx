import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { pipelineApiClient } from "../services/api";
import { isAuthenticated } from "../helpers/auth";
import { TransformationGraph } from "../components/transformation-pipeline/pipeline_builder/TransformationGraph";

export const Route = createFileRoute("/pipeline-view/$pipelineId")({
  loader: async () => {
    if (!isAuthenticated()) {
      throw redirect({ to: "/login" });
    }
  },
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
        console.log('Fetching pipeline with ID:', pipelineId);
        const fetchedPipeline = await pipelineApiClient.getPipeline(pipelineId);
        setPipeline(fetchedPipeline);

        console.log('✅ Fetched pipeline data:', JSON.stringify(fetchedPipeline, null, 2));
        console.log('📊 PIPELINE DATA ANALYSIS:');
        console.log('========================');
        console.log('🔧 Pipeline JSON:', fetchedPipeline.pipeline_json);
        console.log('🎨 Visual JSON:', fetchedPipeline.visual_json);
        console.log('📋 Metadata:', {
          id: fetchedPipeline.id,
          name: fetchedPipeline.name,
          description: fetchedPipeline.description,
          module_count: fetchedPipeline.module_count,
          connection_count: fetchedPipeline.connection_count,
          entry_point_count: fetchedPipeline.entry_point_count
        });

        if (fetchedPipeline.pipeline_json?.modules) {
          console.log('🧩 MODULES DATA:');
          fetchedPipeline.pipeline_json.modules.forEach((module, index) => {
            console.log(`Module ${index + 1}:`, module);
          });
        }

        if (fetchedPipeline.pipeline_json?.connections) {
          console.log('🔗 CONNECTIONS DATA:');
          fetchedPipeline.pipeline_json.connections.forEach((connection, index) => {
            console.log(`Connection ${index + 1}:`, connection);
          });
        }

        if (fetchedPipeline.visual_json?.modules) {
          console.log('📐 VISUAL POSITIONS:');
          Object.entries(fetchedPipeline.visual_json.modules).forEach(([moduleId, position]) => {
            console.log(`${moduleId}:`, position);
          });
        }
        console.log('========================');
      } catch (err: any) {
        console.error('❌ Failed to fetch pipeline:', err);
        setError(err.message || 'Failed to load pipeline');
      } finally {
        setLoading(false);
      }
    };

    fetchPipeline();
  }, [pipelineId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-400">Loading pipeline...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
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
    <div className="h-screen bg-gray-900 flex flex-col">
      {/* Navigation Header */}
      <div className="bg-gray-800 shadow-lg border-b border-gray-700 flex-shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link
                to="/transformation_pipeline"
                className="inline-flex items-center text-gray-400 hover:text-white transition-colors"
              >
                <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back to Pipelines
              </Link>
              <div className="h-6 border-l border-gray-600"></div>
              <div>
                <h1 className="text-2xl font-bold text-white">{pipeline?.name}</h1>
                <p className="mt-1 text-sm text-gray-400">
                  {pipeline?.description || 'No description'} • Pipeline ID: {pipeline?.id}
                </p>
              </div>
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
              <span className="text-sm text-gray-400 bg-gray-700 px-2 py-1 rounded">
                VIEW ONLY
              </span>
            </div>
          </div>

          {/* Pipeline Stats */}
          <div className="flex items-center space-x-6 mt-3 text-sm text-gray-400">
            <span>📦 {pipeline?.module_count || 0} modules</span>
            <span>🔗 {pipeline?.connection_count || 0} connections</span>
            <span>📥 {pipeline?.entry_point_count || 0} entry points</span>
            <span>📅 Created: {new Date(pipeline?.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>

      {/* Pipeline Builder (View Only) - Takes remaining height */}
      <div className="flex-1 flex">
        {pipeline && (
          <TransformationGraph
            moduleTemplates={[]} // No module templates in view mode
            selectedModule={null}
            onModuleSelect={() => {}} // No module selection in view mode
            initialPipeline={pipeline.pipeline_json}
            initialVisual={pipeline.visual_json}
            viewOnly={true} // Add view-only prop
          />
        )}
      </div>
    </div>
  );
}