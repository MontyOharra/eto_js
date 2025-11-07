/**
 * DetailPipelineView
 * Displays executed pipeline visualization with execution values and failed modules
 */

import { useEffect, useRef, useState, useMemo } from "react";
import {
  ExecutedPipelineGraph,
  ExecutedPipelineGraphRef,
} from "../../../pipelines/components/executedViewer-old/ExecutedPipelineGraph";
import { useModules } from "../../../modules";
import { usePipelinesApi } from "../../../pipelines/api";
import type { EtoRunDetail } from "../../types";

interface DetailPipelineViewProps {
  pipelineDefinitionId: number | null;
  runDetail: EtoRunDetail;
}

export function DetailPipelineView({
  pipelineDefinitionId,
  runDetail,
}: DetailPipelineViewProps) {
  const pipelineViewerRef = useRef<ExecutedPipelineGraphRef>(null);
  const { data: moduleTemplates = [] } = useModules();
  const { getPipeline } = usePipelinesApi();

  // Fetch pipeline definition
  const [pipelineDefinition, setPipelineDefinition] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!pipelineDefinitionId) {
      setPipelineDefinition(null);
      return;
    }

    setIsLoading(true);
    getPipeline(pipelineDefinitionId)
      .then((data) => setPipelineDefinition(data))
      .catch((err) => {
        console.error("Failed to fetch pipeline:", err);
        setPipelineDefinition(null);
      })
      .finally(() => setIsLoading(false));
  }, [pipelineDefinitionId, getPipeline]);

  // Auto-fit when pipeline loads or container resizes
  useEffect(() => {
    if (!pipelineViewerRef.current || !pipelineDefinition) return;

    // Initial fit
    const timer = setTimeout(() => {
      pipelineViewerRef.current?.fitView();
    }, 100);

    // Set up resize observer
    const container = document.querySelector(".detail-pipeline-container");
    if (!container) return () => clearTimeout(timer);

    const resizeObserver = new ResizeObserver(() => {
      pipelineViewerRef.current?.fitView();
    });

    resizeObserver.observe(container);

    return () => {
      clearTimeout(timer);
      resizeObserver.disconnect();
    };
  }, [pipelineDefinition]);

  // Build execution values map from API data (no transforms, just Map creation)
  const executionValues = useMemo(() => {
    const valuesMap = new Map<
      string,
      { value: any; type: string; name: string }
    >();

    // Add execution step values
    if (runDetail?.stage_pipeline_execution?.steps) {
      runDetail.stage_pipeline_execution.steps.forEach((step) => {
        // Add input values
        if (step.inputs) {
          Object.entries(step.inputs).forEach(([nodeId, data]) => {
            valuesMap.set(nodeId, {
              value: data.value,
              type: data.type,
              name: data.name,
            });
          });
        }

        // Add output values
        if (step.outputs) {
          Object.entries(step.outputs).forEach(([nodeId, data]) => {
            valuesMap.set(nodeId, {
              value: data.value,
              type: data.type,
              name: data.name,
            });
          });
        }
      });
    }

    // Add entry point values from extraction results
    if (runDetail?.stage_data_extraction?.extraction_results) {
      runDetail.stage_data_extraction.extraction_results.forEach((result) => {
        const entryNodeId = `entry_${result.name}`;
        const fieldValue = result.extracted_value;

        if (fieldValue !== undefined) {
          // Extracted values from backend are always strings
          valuesMap.set(entryNodeId, {
            value: fieldValue,
            type: "str",
            name: result.name,
          });
        }
      });
    }

    return valuesMap;
  }, [runDetail]);

  // Build failed modules list from API data
  const failedModuleIds = useMemo(() => {
    const failed: string[] = [];

    if (runDetail?.stage_pipeline_execution?.steps) {
      runDetail.stage_pipeline_execution.steps.forEach((step) => {
        if (step.error) {
          failed.push(step.module_instance_id);
        }
      });
    }

    return failed;
  }, [runDetail]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400 text-sm">Loading pipeline...</p>
      </div>
    );
  }

  if (!pipelineDefinition || moduleTemplates.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400 text-sm">
          {runDetail?.stage_pipeline_execution?.executed_actions ? (
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
    );
  }

  return (
    <div className="detail-pipeline-container absolute inset-0">
      <ExecutedPipelineGraph
        ref={pipelineViewerRef}
        moduleTemplates={moduleTemplates}
        pipelineState={pipelineDefinition.pipeline_state}
        visualState={pipelineDefinition.visual_state}
        failedModuleIds={failedModuleIds}
        executionValues={executionValues}
      />
    </div>
  );
}
