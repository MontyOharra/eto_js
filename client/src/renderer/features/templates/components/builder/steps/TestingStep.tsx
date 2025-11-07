/**
 * TestingStep
 * Shows template simulation results similar to ETO RunDetailModal
 * Displays PDF with extraction field overlays and pipeline execution visualization
 */

import { useState, useEffect, useRef } from "react";
import { PdfViewer, usePdfViewer } from "../../../../pdf";
import { ExtractedFieldsOverlay } from "../../../../eto/components/EtoRunDetail/ExtractedFieldsOverlay";
import {
  ExecutedPipelineGraph,
  ExecutedPipelineGraphRef,
} from "../../../../pipelines/components/executedViewer-old/ExecutedPipelineGraph";
import type {
  PipelineState,
  VisualState,
} from "../../../../../pipelines/types";
import type { ModuleTemplate } from "../../../../../modules/types";

// Simulation result type (matches ETO run detail but without template/pipeline IDs)
export interface TemplateSimulationResult {
  status: "success" | "failure";
  error_type?: string | null;
  error_message?: string | null;
  data_extraction: {
    extracted_data: Record<string, any> | null;
    extracted_fields_with_boxes?: Array<{
      name: string;
      value: any;
      page: number;
      bbox: [number, number, number, number];
    }>;
  };
  pipeline_execution: {
    status: "success" | "failure";
    error_message?: string | null;
    executed_actions?: Array<{
      action_module_name: string;
      inputs: Record<string, any>;
    }> | null;
    steps: Array<{
      id: number;
      step_number: number;
      module_instance_id: string;
      inputs: Record<string, { name: string; value: any; type: string }> | null;
      outputs: Record<
        string,
        { name: string; value: any; type: string }
      > | null;
      error: {
        type: string;
        message: string;
        details?: any;
      } | null;
    }>;
  };
}

interface TestingStepProps {
  pdfUrl: string;
  viewMode: "summary" | "detail";
  simulationResult: TemplateSimulationResult;
  pipelineState: PipelineState;
  visualState: VisualState;
  moduleTemplates: ModuleTemplate[]; // Available module templates
}

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

export function TestingStep({
  pdfUrl,
  viewMode,
  simulationResult,
  pipelineState,
  visualState,
  moduleTemplates,
}: TestingStepProps) {
  const [specificsWidth, setSpecificsWidth] = useState(60); // Percentage
  const [isDragging, setIsDragging] = useState(false);
  const pdfContainerRef = useRef<HTMLDivElement>(null);
  const pipelineViewerRef = useRef<ExecutedPipelineGraphRef>(null);

  // Process execution data to extract values and failed modules
  const [executionValues, setExecutionValues] = useState<
    Map<string, { value: any; type: string; name: string }>
  >(new Map());
  const [failedModuleIds, setFailedModuleIds] = useState<string[]>([]);

  useEffect(() => {
    const executionValuesMap = new Map<
      string,
      { value: any; type: string; name: string }
    >();
    const failedModules: string[] = [];

    if (simulationResult.pipeline_execution?.steps) {
      simulationResult.pipeline_execution.steps.forEach((step) => {
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
    // Extracted data is keyed by field name
    if (
      simulationResult.data_extraction?.extracted_data &&
      simulationResult.data_extraction?.extracted_fields_with_boxes
    ) {
      simulationResult.data_extraction.extracted_fields_with_boxes.forEach(
        (field) => {
          const entryNodeId = `entry_${field.name}`;
          const fieldValue =
            simulationResult.data_extraction.extracted_data?.[field.name];

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
              name: field.name,
            });
          }
        }
      );
    }

    setExecutionValues(executionValuesMap);
    setFailedModuleIds(failedModules);
  }, [simulationResult]);

  // Resizable divider handlers
  const handleMouseDown = () => {
    setIsDragging(true);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;

    const modal = document.querySelector(".testing-resize-container");
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
      setTimeout(() => {
        pipelineViewerRef.current?.fitView();
      }, 100);
    }
  }, [viewMode]);

  // Auto-fit pipeline viewer when its container is resized
  useEffect(() => {
    if (viewMode !== "detail") return;

    const specificsContainer = document.querySelector(
      ".testing-resize-container .testing-specifics-panel"
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

  return (
    <div className="pr-4 pl-2 py-4 flex h-full testing-resize-container">
      {/* Left Column - Specifics */}
      <div
        className="flex flex-col testing-specifics-panel"
        style={{ width: `${specificsWidth}%` }}
      >
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col flex-1 overflow-hidden">
          <h3 className="text-lg font-semibold text-white mb-3">
            {viewMode === "summary"
              ? simulationResult.status === "success"
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
              {simulationResult.status === "success" &&
              simulationResult.pipeline_execution?.executed_actions ? (
                <pre className="text-gray-300 whitespace-pre-wrap break-words">
                  {JSON.stringify(
                    simulationResult.pipeline_execution.executed_actions,
                    null,
                    2
                  )}
                </pre>
              ) : simulationResult.status === "failure" ? (
                <div className="text-red-300">
                  <p className="font-bold mb-2">
                    Error Type: {simulationResult.error_type || "Unknown"}
                  </p>
                  <p className="mb-2">
                    Message:{" "}
                    {simulationResult.error_message ||
                      "No error message available"}
                  </p>
                  {simulationResult.pipeline_execution?.error_message && (
                    <>
                      <p className="font-bold mb-2 mt-4">Pipeline Error:</p>
                      <p>{simulationResult.pipeline_execution.error_message}</p>
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
              <ExecutedPipelineGraph
                ref={pipelineViewerRef}
                moduleTemplates={moduleTemplates}
                pipelineState={pipelineState}
                visualState={visualState}
                failedModuleIds={failedModuleIds}
                executionValues={executionValues}
              />
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
            <PdfViewer pdfUrl={pdfUrl}>
              <AutoFitOnResize isDragging={isDragging} />
              <PdfViewer.Canvas pdfUrl={pdfUrl}>
                {/* Show extraction field overlay */}
                {simulationResult.data_extraction
                  ?.extracted_fields_with_boxes && (
                  <ExtractedFieldsOverlay
                    fields={simulationResult.data_extraction.extracted_fields_with_boxes.map(
                      (field) => ({
                        field_id: field.name,
                        label: field.name,
                        value: field.value,
                        page: field.page,
                        bbox: field.bbox,
                      })
                    )}
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
  );
}
