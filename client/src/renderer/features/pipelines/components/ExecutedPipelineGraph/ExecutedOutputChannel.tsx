/**
 * ExecutedOutputChannel
 * Wrapper around ExecutedModule with hardcoded values for output channels
 *
 * Output channels reuse the ExecutedModule component but with:
 * - Emerald header color
 * - Channel label as module name
 * - Single input (the value being collected)
 * - No outputs
 */

import { ExecutedModule } from "./ExecutedModule";

interface ExecutedOutputChannelProps {
  data: {
    outputChannelId: string;
    channelType: string;
    channelLabel: string;

    // Input: { [node_id]: { name, value, type } }
    inputs: Record<string, { name: string; value: string; type: string }>;

    // Collected value from pipeline execution (if available)
    collectedValue?: any;

    // Execution status
    status?: "executed" | "failed" | "not_executed";
  };
}

export function ExecutedOutputChannel({ data }: ExecutedOutputChannelProps) {
  const {
    outputChannelId,
    channelLabel,
    inputs,
    collectedValue,
    status = "not_executed",
  } = data;

  // Build inputs with collected value overlay
  const moduleInputs: Record<string, { name: string; value: string; type: string; group_index: number; label: string }> = {};

  Object.entries(inputs).forEach(([nodeId, input]) => {
    moduleInputs[nodeId] = {
      name: input.name,
      value: collectedValue !== undefined ? String(collectedValue) : input.value,
      type: input.type,
      group_index: 0,
      label: "Input",
    };
  });

  const moduleData = {
    moduleName: channelLabel,
    moduleColor: "#FFFFFF", // White
    moduleId: outputChannelId,
    inputs: moduleInputs,
    outputs: {}, // No outputs for output channels
    status,
  };

  return <ExecutedModule data={moduleData} />;
}
