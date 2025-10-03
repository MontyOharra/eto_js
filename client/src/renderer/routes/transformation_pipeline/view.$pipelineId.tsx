import { createFileRoute, useParams, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { PipelineGraph } from "../../components/transformation-pipeline/PipelineGraph";
import { ModuleTemplate } from "../../types/moduleTypes";
import { PipelineState, VisualState } from "../../types/pipelineTypes";

export const Route = createFileRoute("/transformation_pipeline/view/$pipelineId")({
  component: PipelineViewPage,
});

interface Pipeline {
  id: string;
  name: string;
  description: string;
  pipeline_json: PipelineState;
  visual_json: VisualState;
  created_at: string;
  is_active: boolean;
  module_count: number;
  connection_count: number;
}

function PipelineViewPage() {
  const { pipelineId } = useParams({ from: "/transformation_pipeline/view/$pipelineId" });
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);

      try {
        // Fetch both pipeline and module templates in parallel
        const [pipelineResponse, modulesResponse] = await Promise.all([
          fetch(`http://localhost:8090/api/pipelines/${pipelineId}`),
          fetch("http://localhost:8090/api/modules"),
        ]);

        if (!pipelineResponse.ok) {
          throw new Error(`Failed to load pipeline: ${pipelineResponse.status}`);
        }
        if (!modulesResponse.ok) {
          throw new Error(`Failed to load modules: ${modulesResponse.status}`);
        }

        const pipelineData = await pipelineResponse.json();
        const modulesData = await modulesResponse.json();

        setPipeline(pipelineData);
        setModuleTemplates(modulesData.modules || []);
      } catch (err) {
        console.error("Failed to load pipeline data:", err);
        setError(err instanceof Error ? err.message : "Failed to load pipeline");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [pipelineId]);

  // Loading state
  if (loading) {
    return (
      <div className="flex h-screen bg-gray-900">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading pipeline...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !pipeline) {
    return (
      <div className="flex h-screen bg-gray-900">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-red-400 mb-4">
              <svg
                className="w-16 h-16 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-300 mb-2">
              Failed to load pipeline
            </h3>
            <p className="text-gray-500">{error || "Pipeline not found"}</p>
            <Link
              to="/transformation_pipeline"
              className="mt-4 inline-block px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              Back to Pipelines
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="flex h-screen flex-col bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-600 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              to="/transformation_pipeline"
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-white">
                {pipeline.name}
              </h1>
              {pipeline.description && (
                <p className="text-sm text-gray-400">{pipeline.description}</p>
              )}
            </div>
            {pipeline.is_active ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Active
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                Inactive
              </span>
            )}
          </div>
          <div className="flex items-center space-x-4 text-sm text-gray-400">
            <div>
              <span className="font-medium">{pipeline.module_count}</span>{" "}
              modules
            </div>
            <div>
              <span className="font-medium">{pipeline.connection_count}</span>{" "}
              connections
            </div>
            <div>Created {formatDate(pipeline.created_at)}</div>
          </div>
        </div>
      </div>

      {/* Pipeline Graph - Read Only */}
      <div className="flex-1">
        <PipelineGraph
          moduleTemplates={moduleTemplates}
          initialPipelineState={pipeline.pipeline_json}
          initialVisualState={pipeline.visual_json}
          viewOnly={true}
        />
      </div>
    </div>
  );
}
