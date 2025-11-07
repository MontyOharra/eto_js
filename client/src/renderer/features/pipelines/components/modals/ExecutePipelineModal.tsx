/**
 * ExecutePipelineModal
 * Modal for executing a pipeline with entry point values
 * Uses split-panel layout similar to RunDetailModal
 */

import { useState, useEffect } from "react";
import { usePipelinesApi } from "../../api";
import { ExecutedPipelineViewer } from "../ExecutedPipelineViewer";
import type { EntryPoint, PipelineState } from "../../types";

interface ExecutePipelineModalProps {
  isOpen: boolean;
  pipelineId: number | null;
  entryPoints: EntryPoint[];
  onClose: () => void;
}

interface ExecutionResult {
  status: string;
  steps: Array<{
    module_instance_id: string;
    step_number: number;
    inputs: Record<string, { name: string; value: any; type: string }>;
    outputs: Record<string, { name: string; value: any; type: string }>;
    error: string | null;
  }>;
  executed_actions: Record<string, Record<string, any>>;
  error: string | null;
}

type ViewMode = "summary" | "detail";

export function ExecutePipelineModal({
  isOpen,
  pipelineId,
  entryPoints,
  onClose,
}: ExecutePipelineModalProps) {
  const { executePipeline, getPipeline } = usePipelinesApi();

  const [entryValues, setEntryValues] = useState<Record<string, string>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("summary");
  const [executionWidth, setExecutionWidth] = useState(60); // Percentage for left panel
  const [isDragging, setIsDragging] = useState(false);
  const [pipelineState, setPipelineState] = useState<PipelineState | null>(null);

  // Initialize entry values and load pipeline when modal opens
  useEffect(() => {
    if (isOpen && pipelineId) {
      console.log('Entry points received:', entryPoints);
      const initialValues: Record<string, string> = {};
      entryPoints.forEach((ep) => {
        initialValues[ep.name] = "";
      });
      setEntryValues(initialValues);
      setResult(null);
      setError(null);
      setViewMode("summary");

      // Load pipeline state
      async function loadPipeline() {
        try {
          const pipeline = await getPipeline(pipelineId);
          setPipelineState(pipeline.pipeline_state);
        } catch (err) {
          console.error("Failed to load pipeline:", err);
        }
      }
      loadPipeline();
    }
  }, [isOpen, pipelineId, entryPoints, getPipeline]);


  const handleValueChange = (name: string, value: string) => {
    setEntryValues((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleExecute = async () => {
    if (!pipelineId) return;

    // Validate all entry points have values
    const missingEntries = entryPoints.filter(
      (ep) => !entryValues[ep.name]?.trim()
    );
    if (missingEntries.length > 0) {
      setError(
        `Please provide values for: ${missingEntries.map((ep) => ep.name).join(", ")}`
      );
      return;
    }

    setIsExecuting(true);
    setError(null);
    setResult(null);

    try {
      const executionResult = await executePipeline(pipelineId, {"entry_values":entryValues});
      setResult(executionResult);
    } catch (err) {
      console.error("Pipeline execution failed:", err);
      setError(
        err instanceof Error ? err.message : "Pipeline execution failed"
      );
    } finally {
      setIsExecuting(false);
    }
  };

  const handleClose = () => {
    setEntryValues({});
    setResult(null);
    setError(null);
    onClose();
  };

  // Resizable divider handlers
  const handleMouseDown = () => {
    setIsDragging(true);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;

    const modal = document.querySelector(".resize-container");
    if (!modal) return;

    const rect = modal.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const percentage = (offsetX / rect.width) * 100;

    // Constrain between 30% and 70%
    const constrainedPercentage = Math.min(Math.max(percentage, 30), 70);
    setExecutionWidth(constrainedPercentage);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Attach/detach mouse event listeners for resizing
  useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-[95vw] h-[95vh] overflow-hidden border border-gray-700 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold text-white">
              Pipeline Execution Tester
            </h2>

            {/* View Mode Toggle - Only show after execution */}
            {result && (
              <div className="flex items-center bg-gray-800 rounded-lg p-1 border-l border-gray-600 ml-4">
                <button
                  onClick={() => setViewMode("summary")}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    viewMode === "summary"
                      ? "bg-blue-600 text-white"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  Summary
                </button>
                <button
                  onClick={() => setViewMode("detail")}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    viewMode === "detail"
                      ? "bg-blue-600 text-white"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  Detail
                </button>
              </div>
            )}
          </div>

          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content - Split Panel Layout */}
        <div className="flex-1 overflow-hidden">
          <div className="pr-4 pl-2 py-4 flex h-full resize-container">
            {/* Left Panel - Execution Auditor */}
            <div
              className="flex flex-col execution-panel"
              style={{ width: `${executionWidth}%` }}
            >
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col flex-1 overflow-hidden">
                <h3 className="text-lg font-semibold text-white mb-3">
                  {!result
                    ? "Execution Auditor"
                    : result.status === "success"
                      ? "Execution Results"
                      : "Execution Failed"}
                </h3>

                {/* Scrollable content area */}
                <div className="flex-1 overflow-auto bg-gray-900 rounded p-3 relative">
                  {!result ? (
                    // Before execution
                    <div className="flex items-center justify-center h-full">
                      <p className="text-gray-400 text-sm">
                        Execute pipeline to see results here
                      </p>
                    </div>
                  ) : (
                    <>
                      {/* Summary View - Actions/Errors */}
                      <div
                        className={`font-mono text-xs ${viewMode === "summary" ? "" : "hidden"}`}
                      >
                        {result.status === "success" &&
                        Object.keys(result.executed_actions).length > 0 ? (
                          <pre className="text-gray-300 whitespace-pre-wrap break-words">
                            {JSON.stringify(result.executed_actions, null, 2)}
                          </pre>
                        ) : result.status === "failed" ? (
                          <div className="text-red-300">
                            <p className="font-bold mb-2">Execution Failed</p>
                            <p className="mb-2">
                              {result.error || "No error message available"}
                            </p>
                          </div>
                        ) : (
                          <p className="text-gray-400">No actions executed</p>
                        )}
                      </div>

                      {/* Detail View - Pipeline Visualization */}
                      <div
                        className={`absolute inset-0 ${viewMode === "detail" ? "" : "hidden"}`}
                      >
                        {pipelineState ? (
                          <ExecutedPipelineViewer
                            pipelineId={pipelineId}
                            pipelineState={pipelineState}
                            executionSteps={result.steps}
                            entryValues={(() => {
                              // Build entry values map: { node_id: { name, value, type } }
                              const entryValuesMap: Record<string, { name: string; value: any; type: string }> = {};
                              entryPoints.forEach((ep) => {
                                const value = entryValues[ep.name];
                                if (value !== undefined && value !== "") {
                                  entryValuesMap[ep.node_id] = {
                                    name: ep.name,
                                    value: value,
                                    type: ep.type,
                                  };
                                }
                              });
                              console.log('Built entryValuesMap:', entryValuesMap);
                              return entryValuesMap;
                            })()}
                          />
                        ) : (
                          <div className="flex items-center justify-center h-full">
                            <p className="text-gray-400">
                              Loading pipeline data...
                            </p>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Resizable Divider */}
            <div
              className="w-1 bg-gray-700 hover:bg-blue-500 cursor-col-resize transition-colors flex-shrink-0 mx-1"
              onMouseDown={handleMouseDown}
              style={{
                userSelect: "none",
                backgroundColor: isDragging ? "#3B82F6" : undefined,
              }}
            />

            {/* Right Panel - Entry Points */}
            <div
              className="flex flex-col"
              style={{ width: `${100 - executionWidth}%` }}
            >
              <div className="bg-gray-800 border border-gray-700 rounded-lg flex-1 overflow-hidden p-4 flex flex-col">
                <h3 className="text-lg font-semibold text-white mb-4">
                  Entry Points
                </h3>

                <div className="flex-1 overflow-y-auto space-y-4">
                  {entryPoints.map((ep) => (
                    <div key={ep.node_id}>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        {ep.name}
                        <span className="text-gray-500 ml-2">({ep.type})</span>
                      </label>
                      <input
                        type="text"
                        value={entryValues[ep.name] || ""}
                        onChange={(e) =>
                          handleValueChange(ep.name, e.target.value)
                        }
                        placeholder={`Enter value for ${ep.name}`}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
                        disabled={isExecuting}
                      />
                    </div>
                  ))}
                </div>

                {/* Error Display */}
                {error && (
                  <div className="mt-4 bg-red-900 border border-red-700 rounded-lg p-3">
                    <p className="text-red-200 text-sm">{error}</p>
                  </div>
                )}

                {/* Execute Button */}
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={handleExecute}
                    disabled={isExecuting}
                    className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isExecuting ? "Executing..." : "Execute"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-3 border-t border-gray-700 flex-shrink-0">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-800 transition-colors text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
