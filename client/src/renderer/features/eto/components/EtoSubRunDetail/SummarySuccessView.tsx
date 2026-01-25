/**
 * SummarySuccessView
 * Displays success state for completed ETO sub-runs with output channel data
 */

import { useEffect, useState } from "react";
import { usePipelinesApi } from "../../../pipelines/api";
import { useOutputChannels } from "../../../modules";
import {
  formatValue,
  formatChannelLabel,
  getChannelColor,
  sortOutputChannelsByCategory,
  type OutputChannelResult,
} from "../../utils";
import type { EtoSubRunFullDetail } from "../../types";

interface SummarySuccessViewProps {
  runDetail: EtoSubRunFullDetail;
}

export function SummarySuccessView({ runDetail }: SummarySuccessViewProps) {
  const { getPipeline } = usePipelinesApi();
  const { data: outputChannelTypes } = useOutputChannels();
  const [pipelineState, setPipelineState] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const pipelineDefinitionId = runDetail.stage_pipeline_execution?.pipeline_definition_id;

  // Fetch pipeline definition to get output channel info
  useEffect(() => {
    if (!pipelineDefinitionId) {
      setPipelineState(null);
      return;
    }

    setIsLoading(true);
    getPipeline(pipelineDefinitionId)
      .then((data) => {
        setPipelineState(data.pipeline_state);
      })
      .catch((err) => {
        console.error("Failed to fetch pipeline:", err);
        setPipelineState(null);
      })
      .finally(() => setIsLoading(false));
  }, [pipelineDefinitionId, getPipeline]);

  // Extract output channel results from execution steps
  const outputChannelResults = (() => {
    if (!pipelineState || !runDetail.stage_pipeline_execution?.steps) {
      return [];
    }

    const results: OutputChannelResult[] = [];

    pipelineState.output_channels?.forEach((outputChannel: any) => {
      // Find the execution step for this output channel
      const executionStep = runDetail.stage_pipeline_execution?.steps.find(
        (step) => step.module_instance_id === outputChannel.output_channel_instance_id
      );

      if (executionStep?.inputs) {
        // Get the first input's value property (the collected value)
        const inputData = Object.values(executionStep.inputs)[0] as { value?: unknown } | undefined;
        const collectedValue = inputData?.value;

        // Get label from output channel types
        const channelTypeInfo = outputChannelTypes?.find(
          (oct) => oct.name === outputChannel.channel_type
        );
        const label = channelTypeInfo?.label || formatChannelLabel(outputChannel.channel_type);

        results.push({
          label,
          channelType: outputChannel.channel_type,
          value: collectedValue,
        });
      }
    });

    // Sort results by category order
    return sortOutputChannelsByCategory(results, outputChannelTypes);
  })();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400 text-sm">Loading results...</p>
      </div>
    );
  }

  if (outputChannelResults.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <div className="text-green-400 mb-4">
          <svg
            className="mx-auto h-16 w-16"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <p className="text-green-400 font-medium text-lg mb-2">
          Pipeline Completed Successfully
        </p>
        <p className="text-gray-400 text-sm">
          No output channel data available
        </p>
      </div>
    );
  }

  const colors = getChannelColor();

  return (
    <div className="space-y-2">
      {outputChannelResults.map((result, index) => {
        return (
          <div
            key={index}
            className={`flex items-start gap-3 py-2 px-3 rounded border ${colors.bg} ${colors.border}`}
          >
            <span className={`text-sm w-40 flex-shrink-0 font-medium ${colors.text}`}>
              {result.label}
            </span>
            <span className="text-sm text-white break-words flex-1">
              {formatValue(result.value)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
