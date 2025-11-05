/**
 * Run Detail Modal
 * Displays detailed information about an ETO run including PDF info,
 * execution details, and allows viewing the PDF and specifics
 */

import { useState, useEffect, useRef, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { PdfViewer, usePdfViewer } from "../../../pdf";
import { useEtoRunDetail, getPdfDownloadUrl } from "../../hooks";
import { StatusBadge } from "../EtoRunTable/StatusBadge";
import { ExtractedFieldsOverlay } from "../EtoRunDetail/ExtractedFieldsOverlay";
import {
  ExecutedPipelineGraph,
  ExecutedPipelineGraphRef,
} from "../../../pipelines/components/ExecutedPipelineGraph";
import { useModules } from '../../../modules';
import { apiClient } from "../../../../shared/api/client";
import { API_CONFIG } from "../../../../shared/api/config";
import type { EtoRunDetail } from "../../types";
import type { PipelineState, VisualState } from "../../../pipelines/types";

interface RunDetailModalProps {
  isOpen: boolean;
  runId: number | null;
  onClose: () => void;
}

type ViewMode = "summary" | "detail";

// Helper component to trigger fit-to-width on resize (only during divider drag)
function AutoFitOnResize({ isDragging }: { isDragging: boolean }) {
  const { fitToWidth, pdfDimensions } = usePdfViewer();
  const pdfViewerRef = useRef<HTMLDivElement>(null);
  const hasAutoFittedOnLoad = useRef(false);

  // Auto-fit when PDF first loads
  useEffect(() => {
    if (
      !pdfDimensions ||
      !pdfViewerRef.current ||
      hasAutoFittedOnLoad.current
    ) {
      return;
    }

    const pdfViewerContainer = pdfViewerRef.current.parentElement;
    if (!pdfViewerContainer) {
      return;
    }

    // Trigger fit-to-width on initial load
    const containerWidth = pdfViewerContainer.clientWidth;
    const sidebarWidth = 64; // w-16 = 64px
    fitToWidth(containerWidth, sidebarWidth);
    hasAutoFittedOnLoad.current = true;
  }, [pdfDimensions, fitToWidth]);

  // Trigger fit-to-width on resize, but ONLY when dragging the divider
  useEffect(() => {
    if (!isDragging || !pdfViewerRef.current || !pdfDimensions) {
      return;
    }

    // Get the actual PdfViewer container (same element the fit button measures)
    const pdfViewerContainer = pdfViewerRef.current.parentElement;
    if (!pdfViewerContainer) {
      return;
    }

    const resizeObserver = new ResizeObserver(() => {
      if (!pdfViewerContainer || !isDragging) {
        return;
      }

      const containerWidth = pdfViewerContainer.clientWidth;
      const sidebarWidth = 64; // w-16 = 64px
      fitToWidth(containerWidth, sidebarWidth);
    });

    resizeObserver.observe(pdfViewerContainer);

    return () => {
      resizeObserver.disconnect();
    };
  }, [fitToWidth, pdfDimensions, isDragging]);

  return <div ref={pdfViewerRef} style={{ display: "none" }} />;
}

export function RunDetailModal({
  isOpen,
  runId,
  onClose,
}: RunDetailModalProps) {
  // Use TanStack Query hook to fetch run details
  const {
    data: runDetail,
    isLoading,
    error: queryError,
  } = useEtoRunDetail(isOpen ? runId : null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("summary");
  const [specificsWidth, setSpecificsWidth] = useState(60); // Percentage
  const [isDragging, setIsDragging] = useState(false);
  const pdfContainerRef = useRef<HTMLDivElement>(null);
  const pipelineViewerRef = useRef<ExecutedPipelineGraphRef>(null);

  const error = queryError ? "Failed to load run details" : null;

  // Fetch module templates using TanStack Query
  const { data: moduleTemplates = [] } = useModules();

  // Fetch pipeline definition when pipeline_definition_id is available
  const pipelineDefinitionId =
    runDetail?.stage_pipeline_execution?.pipeline_definition_id;
  const { data: pipelineDefinition } = useQuery({
    queryKey: ["pipeline", pipelineDefinitionId],
    queryFn: async () => {
      if (!pipelineDefinitionId) return null;

      const response = await apiClient.get<any>(
        `${API_CONFIG.ENDPOINTS.PIPELINES}/${pipelineDefinitionId}`
      );
      const data = response.data;

      // Transform backend snake_case to frontend camelCase
      if (data.visual_state?.entry_points) {
        data.visual_state.entryPoints = data.visual_state.entry_points;
        delete data.visual_state.entry_points;
      }

      return data;
    },
    enabled: !!pipelineDefinitionId && isOpen,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Transform extraction results for overlay display
  const extractedFieldsForOverlay = useMemo(() => {
    if (!runDetail?.stage_data_extraction?.extraction_results) return [];

    return runDetail.stage_data_extraction.extraction_results.map((result) => ({
      field_id: result.name,
      label: result.description || result.name,
      value: result.extracted_value,
      page: result.page,
      bbox: result.bbox,
    }));
  }, [runDetail?.stage_data_extraction?.extraction_results]);

  // Convert extraction results to key-value dict (for backward compatibility)
  const extractedData = useMemo(() => {
    if (!runDetail?.stage_data_extraction?.extraction_results) return undefined;

    return runDetail.stage_data_extraction.extraction_results.reduce(
      (acc, result) => {
        acc[result.name] = result.extracted_value;
        return acc;
      },
      {} as Record<string, string>
    );
  }, [runDetail?.stage_data_extraction?.extraction_results]);

  // Process execution steps into executionValues Map and failedModuleIds array
  const [executionValues, failedModuleIds] = useMemo(() => {
    const executionValuesMap = new Map<
      string,
      { value: any; type: string; name: string }
    >();
    const failedModules: string[] = [];

    if (runDetail?.stage_pipeline_execution?.steps) {
      runDetail.stage_pipeline_execution.steps.forEach((step) => {
        // Collect all input node IDs and values
        if (step.inputs) {
          Object.entries(step.inputs).forEach(([nodeId, data]) => {
            executionValuesMap.set(nodeId, {
              value: data.value,
              type: data.type,
              name: data.name,
            });
          });
        }

        // Collect all output node IDs and values
        if (step.outputs) {
          Object.entries(step.outputs).forEach(([nodeId, data]) => {
            executionValuesMap.set(nodeId, {
              value: data.value,
              type: data.type,
              name: data.name,
            });
          });
        }

        // Track failed modules
        if (step.error) {
          failedModules.push(step.module_instance_id);
        }
      });
    }

    // Add entry point values from extracted data
    // Entry points use node_id format: entry_${field_name}
    if (runDetail?.stage_data_extraction?.extraction_results) {
      runDetail.stage_data_extraction.extraction_results.forEach((result) => {
        const entryNodeId = `entry_${result.name}`;
        const fieldValue = result.extracted_value;

        if (fieldValue !== undefined) {
          // Determine type from the value
          let valueType = typeof fieldValue;
          if (valueType === "object" && fieldValue instanceof Date) {
            valueType = "datetime";
          } else if (valueType === "number") {
            valueType = Number.isInteger(fieldValue) ? "int" : "float";
          } else if (valueType === "string") {
            valueType = "str";
          }

          executionValuesMap.set(entryNodeId, {
            value: fieldValue,
            type: valueType,
            name: result.name,
          });
        }
      });
    }

    return [executionValuesMap, failedModules] as const;
  }, [
    runDetail?.stage_pipeline_execution?.steps,
    runDetail?.stage_data_extraction?.extraction_results,
  ]);

  // Reset to summary view when modal opens
  useEffect(() => {
    if (isOpen) {
      setViewMode("summary");
    }
  }, [isOpen]);

  // Set PDF URL when run detail is loaded
  useEffect(() => {
    if (runDetail?.pdf.id) {
      const url = getPdfDownloadUrl(runDetail.pdf.id);
      setPdfUrl(url);
    }
  }, [runDetail?.pdf.id]);

  const handlePdfError = (pdfError: Error) => {
    console.error("PDF load error:", pdfError);
    // PDF errors are logged but don't update the error state
    // TanStack Query handles API errors
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

    // Constrain between 20% and 80%
    const constrainedPercentage = Math.min(Math.max(percentage, 20), 80);
    setSpecificsWidth(constrainedPercentage);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Attach/detach mouse event listeners
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

  // Fit pipeline view when switching to detail mode
  useEffect(() => {
    if (viewMode === "detail" && pipelineViewerRef.current) {
      // Delay to ensure the pipeline is rendered
      setTimeout(() => {
        pipelineViewerRef.current?.fitView();
      }, 100);
    }
  }, [viewMode]);

  // Auto-fit pipeline viewer when its container is resized (e.g., dragging divider)
  useEffect(() => {
    if (viewMode !== "detail") return;

    const specificsContainer = document.querySelector(
      ".resize-container .specifics-panel"
    );
    if (!specificsContainer) return;

    const resizeObserver = new ResizeObserver(() => {
      if (pipelineViewerRef.current) {
        pipelineViewerRef.current.fitView();
      }
    });

    resizeObserver.observe(specificsContainer);

    return () => {
      resizeObserver.disconnect();
    };
  }, [viewMode]);

  // Format file size
  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return "Unknown";
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  // Format duration
  const formatDuration = (
    startedAt: string | null,
    completedAt: string | null
  ): string => {
    if (!startedAt || !completedAt) return "N/A";
    const start = new Date(startedAt).getTime();
    const end = new Date(completedAt).getTime();
    const durationMs = end - start;
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${seconds}s`;
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string | null): string => {
    if (!timestamp) return "N/A";
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  if (!isOpen || !runId) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-[95vw] h-[95vh] overflow-hidden border border-gray-700 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <h2 className="text-xl font-semibold text-white">
                ETO Run Details
              </h2>
              {runDetail && <StatusBadge status={runDetail.status} />}
            </div>

            {/* View Mode Toggle */}
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

            {runDetail && (
              <>
                {/* Source */}
                <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                  <span className="text-gray-400">Source:</span>{" "}
                  {runDetail.source.type === "email" ? (
                    <span className="font-mono">
                      {runDetail.source.sender_email}
                    </span>
                  ) : (
                    "Manual Upload"
                  )}
                </div>

                {/* Template */}
                {runDetail.matched_template && (
                  <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                    <span className="text-gray-400">Template:</span>{" "}
                    {runDetail.matched_template.template_name}{" "}
                    <span className="text-gray-500">
                      (v{runDetail.matched_template.version_num})
                    </span>
                  </div>
                )}

                {/* Duration */}
                <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                  <span className="text-gray-400">Duration:</span>{" "}
                  <span className="font-mono">
                    {formatDuration(
                      runDetail.started_at,
                      runDetail.completed_at
                    )}
                  </span>
                </div>
              </>
            )}
          </div>

          <button
            onClick={onClose}
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

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-blue-400">Loading run details...</div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
                <p className="text-red-200">{error}</p>
              </div>
            </div>
          )}

          {!isLoading && !error && runDetail && (
            <div className="pr-4 pl-2 py-4 flex h-full resize-container">
              {/* Left Column - Specifics */}
              <div
                className="flex flex-col specifics-panel"
                style={{ width: `${specificsWidth}%` }}
              >
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col flex-1 overflow-hidden">
                  <h3 className="text-lg font-semibold text-white mb-3">
                    {viewMode === "summary"
                      ? runDetail.status === "success"
                        ? "Actions Executed"
                        : "Error Details"
                      : "Transformation Pipeline"}
                  </h3>

                  {/* Scrollable content area */}
                  <div className="flex-1 overflow-auto bg-gray-900 rounded p-3 relative">
                    {/* Summary View - Actions/Errors (keep mounted, toggle visibility) */}
                    <div
                      className={`font-mono text-xs ${viewMode === "summary" ? "" : "hidden"}`}
                    >
                      {runDetail.status === "success" &&
                      runDetail.stage_pipeline_execution?.executed_actions ? (
                        <pre className="text-gray-300 whitespace-pre-wrap break-words">
                          {JSON.stringify(
                            runDetail.stage_pipeline_execution.executed_actions,
                            null,
                            2
                          )}
                        </pre>
                      ) : runDetail.status === "failure" ? (
                        <div className="text-red-300">
                          <p className="font-bold mb-2">
                            Error Type: {runDetail.error_type || "Unknown"}
                          </p>
                          <p className="mb-2">
                            Message:{" "}
                            {runDetail.error_message ||
                              "No error message available"}
                          </p>
                          {runDetail.error_details && (
                            <>
                              <p className="font-bold mb-2 mt-4">
                                Error Details:
                              </p>
                              <pre className="text-xs whitespace-pre-wrap">
                                {runDetail.error_details}
                              </pre>
                            </>
                          )}
                        </div>
                      ) : (
                        <p className="text-gray-400">No details available</p>
                      )}
                    </div>

                    {/* Detail View - Pipeline Visualization (keep mounted, toggle visibility) */}
                    <div
                      className={`absolute inset-0 ${viewMode === "detail" ? "" : "hidden"}`}
                    >
                      {pipelineDefinition && moduleTemplates.length > 0 ? (
                        <ExecutedPipelineGraph
                          ref={pipelineViewerRef}
                          moduleTemplates={moduleTemplates}
                          pipelineState={pipelineDefinition.pipeline_state}
                          visualState={pipelineDefinition.visual_state}
                          failedModuleIds={failedModuleIds}
                          executionValues={executionValues}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full">
                          <p className="text-gray-400 text-sm">
                            {runDetail?.stage_pipeline_execution
                              ?.executed_actions ? (
                              <>
                                <span className="block mb-2">
                                  Detailed pipeline visualization not available
                                </span>
                                <span className="block text-xs text-gray-500">
                                  See Summary view for executed actions
                                </span>
                              </>
                            ) : (
                              "No pipeline data available"
                            )}
                          </p>
                        </div>
                      )}
                    </div>
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

              {/* Right Column - PDF Viewer */}
              <div
                className="flex flex-col"
                style={{ width: `${100 - specificsWidth}%` }}
                ref={pdfContainerRef}
              >
                <div className="bg-gray-800 border border-gray-700 rounded-lg flex-1 overflow-hidden relative pr-4 pl-1 py-4">
                  {pdfUrl ? (
                    <PdfViewer pdfUrl={pdfUrl} onError={handlePdfError}>
                      <AutoFitOnResize isDragging={isDragging} />
                      <PdfViewer.Canvas
                        pdfUrl={pdfUrl}
                        onError={handlePdfError}
                      >
                        {/* Show extraction field overlay in detail view */}
                        {viewMode === "detail" &&
                          extractedFieldsForOverlay.length > 0 && (
                            <ExtractedFieldsOverlay
                              fields={extractedFieldsForOverlay}
                            />
                          )}
                      </PdfViewer.Canvas>
                      <PdfViewer.ControlsSidebar position="right" />
                    </PdfViewer>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <p className="text-gray-400">No PDF available</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-3 border-t border-gray-700 flex-shrink-0">
          {runDetail && (
            <div className="flex items-center space-x-4 text-xs text-gray-400">
              <div>
                <span className="text-gray-500">Started:</span>{" "}
                <span className="font-mono">
                  {formatTimestamp(runDetail.started_at)}
                </span>
              </div>
              {runDetail.completed_at && (
                <div>
                  <span className="text-gray-500">Completed:</span>{" "}
                  <span className="font-mono">
                    {formatTimestamp(runDetail.completed_at)}
                  </span>
                </div>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-800 transition-colors text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
