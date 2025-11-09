/**
 * PipelineViewerModal
 * Read-only viewer for pipeline definitions
 * Displays pipeline graph without module selector or edit capabilities
 */

import { useState, useEffect } from "react";
import { PipelineGraph } from "../PipelineGraph/PipelineGraph";
import { ExecutePipelineModal } from "../ExecutePipelineModal";
import { usePipelinesApi, PipelineDetail } from "../../";
import { useModules } from "../../../modules";

interface PipelineViewerModalProps {
  isOpen: boolean;
  pipelineId: number;
  onClose: () => void;
}

export function PipelineViewerModal({
  isOpen,
  pipelineId,
  onClose,
}: PipelineViewerModalProps) {
  const { getPipeline } = usePipelinesApi();

  // Fetch modules using TanStack Query
  const { data: modules = [] } = useModules();

  const [pipeline, setPipeline] = useState<PipelineDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showExecuteModal, setShowExecuteModal] = useState(false);

  // Load pipeline when modal opens
  useEffect(() => {
    if (!isOpen || !pipelineId) {
      setPipeline(null);
      setError(null);
      return;
    }

    async function loadData() {
      setIsLoading(true);
      setError(null);

      try {
        const pipelineData = await getPipeline(pipelineId);
        setPipeline(pipelineData);
      } catch (err) {
        console.error("Failed to load pipeline:", err);
        setError(
          err instanceof Error ? err.message : "Failed to load pipeline"
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [isOpen, pipelineId, getPipeline]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setPipeline(null);
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75">
      <div className="bg-gray-900 rounded-lg shadow-xl w-[95vw] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-white">
              Pipeline #{pipelineId}
            </h2>
            <p className="text-sm text-gray-400 mt-1">Read-only view</p>
          </div>
          <div className="flex items-center gap-3">
            {pipeline && (
              <button
                onClick={() => setShowExecuteModal(true)}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors font-medium"
              >
                Execute Pipeline
              </button>
            )}
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {isLoading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-white text-lg mb-2">
                  Loading pipeline...
                </div>
                <div className="text-gray-400 text-sm">Please wait</div>
              </div>
            </div>
          )}

          {error && (
            <div className="h-full flex items-center justify-center p-6">
              <div className="bg-red-900 border border-red-700 rounded-lg p-6 max-w-md">
                <h3 className="text-xl font-bold text-red-300 mb-2">Error</h3>
                <p className="text-red-200">{error}</p>
              </div>
            </div>
          )}

          {!isLoading && !error && pipeline && (
            <PipelineGraph
              moduleTemplates={modules}
              selectedModuleId={null}
              onModulePlaced={() => {}}
              viewOnly={true}
              initialPipelineState={pipeline.pipeline_state}
              initialVisualState={pipeline.visual_state}
            />
          )}
        </div>
      </div>

      {/* Execute Pipeline Modal */}
      {pipeline && (
        <ExecutePipelineModal
          isOpen={showExecuteModal}
          pipelineId={pipelineId}
          entryPoints={pipeline.pipeline_state.entry_points}
          onClose={() => setShowExecuteModal(false)}
        />
      )}
    </div>
  );
}
