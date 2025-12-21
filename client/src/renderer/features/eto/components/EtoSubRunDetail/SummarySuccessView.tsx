/**
 * SummarySuccessView
 * Displays success state for completed ETO sub-runs with output channel data
 */

import { useEffect, useState } from "react";
import { usePipelinesApi } from "../../../pipelines/api";
import { useOutputChannels } from "../../../modules";
import type { EtoSubRunFullDetail } from "../../types";

interface SummarySuccessViewProps {
  runDetail: EtoSubRunFullDetail;
}

/**
 * Check if a string is an ISO datetime format
 */
function isISODateTime(value: string): boolean {
  const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
  return isoPattern.test(value);
}

/**
 * Format ISO datetime string to human readable format
 */
function formatISODateTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    return date.toLocaleString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return isoString;
  }
}

/**
 * Check if value is a dim object (has height, length, width, qty, weight)
 */
function isDimObject(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    "height" in value &&
    "length" in value &&
    "width" in value &&
    "qty" in value &&
    "weight" in value
  );
}

/**
 * Format a single dim object as "qty - HxLxW @weightlbs"
 */
function formatDim(dim: Record<string, unknown>): string {
  const h = dim.height ?? 0;
  const l = dim.length ?? 0;
  const w = dim.width ?? 0;
  const qty = dim.qty ?? 1;
  const weight = dim.weight ?? 0;
  return `${qty} - ${h}x${l}x${w} @${weight}lbs`;
}

/**
 * Format a value for display, handling datetime objects, ISO strings, and dims
 */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "-";
  }

  // Check if it's an ISO datetime string
  if (typeof value === "string") {
    if (isISODateTime(value)) {
      return formatISODateTime(value);
    }
    return value;
  }

  // Check if it's a datetime object (has year, month, day properties)
  if (typeof value === "object" && value !== null) {
    const obj = value as Record<string, unknown>;

    // Check for dim object
    if (isDimObject(value)) {
      return formatDim(obj);
    }

    // Check for list[dim] - array of dim objects
    if (Array.isArray(value) && value.length > 0 && isDimObject(value[0])) {
      return "[" + value.map((d) => formatDim(d as Record<string, unknown>)).join(", ") + "]";
    }

    if ("year" in obj && "month" in obj && "day" in obj) {
      const year = obj.year as number;
      const month = obj.month as number;
      const day = obj.day as number;

      // Format date part
      let result = `${month}/${day}/${year}`;

      // Add time if present
      if ("hour" in obj && "minute" in obj) {
        const hour = obj.hour as number;
        const minute = obj.minute as number;
        const period = hour >= 12 ? "PM" : "AM";
        const displayHour = hour % 12 || 12;
        result += ` ${displayHour}:${String(minute).padStart(2, "0")} ${period}`;
      }

      return result;
    }

    // For other objects, stringify nicely
    return JSON.stringify(value);
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return String(value);
}

/**
 * Format channel type to human-readable label
 */
function formatChannelLabel(channelType: string): string {
  return channelType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Get color classes for a channel type
 */
function getChannelColor(channelType: string): { bg: string; border: string; text: string } {
  // Time-related channels
  if (channelType.includes("time") || channelType.includes("date")) {
    return {
      bg: "bg-purple-500/10",
      border: "border-purple-500/30",
      text: "text-purple-300",
    };
  }

  // Address-related channels
  if (channelType.includes("address")) {
    return {
      bg: "bg-blue-500/10",
      border: "border-blue-500/30",
      text: "text-blue-300",
    };
  }

  // Identifier channels (hawb, mawb, order numbers)
  if (channelType.includes("hawb") || channelType.includes("mawb") || channelType.includes("order")) {
    return {
      bg: "bg-amber-500/10",
      border: "border-amber-500/30",
      text: "text-amber-300",
    };
  }

  // Numeric channels (pieces, weight)
  if (channelType.includes("pieces") || channelType.includes("weight")) {
    return {
      bg: "bg-green-500/10",
      border: "border-green-500/30",
      text: "text-green-300",
    };
  }

  // Notes channels
  if (channelType.includes("notes")) {
    return {
      bg: "bg-gray-500/10",
      border: "border-gray-500/30",
      text: "text-gray-300",
    };
  }

  // Default
  return {
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/30",
    text: "text-cyan-300",
  };
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

    const results: { label: string; channelType: string; value: unknown }[] = [];

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
          (oct) => oct.channel_type === outputChannel.channel_type
        );
        const label = channelTypeInfo?.label || formatChannelLabel(outputChannel.channel_type);

        results.push({
          label,
          channelType: outputChannel.channel_type,
          value: collectedValue,
        });
      }
    });

    return results;
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

  return (
    <div className="space-y-2">
      {outputChannelResults.map((result, index) => {
        const colors = getChannelColor(result.channelType);
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
