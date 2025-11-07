/**
 * DetailPipelineView
 * Displays executed pipeline visualization with execution values and failed modules
 */

import { useEffect, useState, useMemo } from "react";
import { ExecutedPipelineViewer } from "../../../pipelines/components/ExecutedPipelineViewer/ExecutedPipelineViewer";
import { usePipelinesApi } from "../../../pipelines/api";
import type { EtoRunDetail } from "../../types";
import type { ExecutionStepResult } from "../../../pipelines/api/types";

interface DetailPipelineViewProps {
  pipelineDefinitionId: number | null;
  runDetail: EtoRunDetail;
}

export function DetailPipelineView({
  pipelineDefinitionId,
  runDetail,
}: DetailPipelineViewProps) {
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

  // Convert execution steps to new API format
  const executionSteps: ExecutionStepResult[] = useMemo(() => {
    if (!runDetail?.stage_pipeline_execution?.steps) {
      return [];
    }

    return runDetail.stage_pipeline_execution.steps.map((step) => ({
      module_instance_id: step.module_instance_id,
      step_number: step.step_number,
      inputs: step.inputs || {},
      outputs: step.outputs || {},
      error: step.error || null,
    }));
  }, [runDetail]);

  // Convert entry values to new API format
  // Map extraction results by node_id (from entry point outputs) instead of by name
  const entryValues = useMemo(() => {
    const values: Record<string, { name: string; value: any; type: string }> = {};

    if (!pipelineDefinition?.pipeline_state || !runDetail?.stage_data_extraction?.extraction_results) {
      return values;
    }

    // Create a map of entry point name -> output node_id
    const entryNameToNodeId = new Map<string, string>();
    pipelineDefinition.pipeline_state.entry_points.forEach((ep: any) => {
      if (ep.outputs && ep.outputs[0]) {
        entryNameToNodeId.set(ep.name, ep.outputs[0].node_id);
      }
    });

    // Map extraction results to node_ids
    runDetail.stage_data_extraction.extraction_results.forEach((result) => {
      if (result.extracted_value !== undefined) {
        const nodeId = entryNameToNodeId.get(result.name);
        if (nodeId) {
          values[nodeId] = {
            name: result.name,
            value: result.extracted_value,
            type: "str",
          };
        }
      }
    });

    return values;
  }, [runDetail, pipelineDefinition]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400 text-sm">Loading pipeline...</p>
      </div>
    );
  }

  if (!pipelineDefinition) {
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
      <ExecutedPipelineViewer
        pipelineId={pipelineDefinitionId}
        pipelineState={pipelineDefinition.pipeline_state}
        executionSteps={executionSteps}
        entryValues={entryValues}
      />
    </div>
  );
}
