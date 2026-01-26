/**
 * ExecutedModule
 * Simplified read-only module component for execution visualization
 * Composed of ExecutedModuleHeader and ExecutedModuleBody
 */

import { ExecutedModuleHeader } from "./ExecutedModuleHeader";
import { ExecutedModuleBody } from "./ExecutedModuleBody";

interface ExecutedModuleProps {
  data: {
    // Header info
    moduleId: string;
    moduleName: string;
    moduleColor: string;

    // Inputs: { [node_id]: { name: "node_name", value: "actual_value", type: "str", group_index: 0, label: "Group" } }
    inputs: Record<string, { name: string; value: string; type: string; group_index: number; label: string }>;

    // Outputs: { [node_id]: { name: "node_name", value: "actual_value", type: "str", group_index: 0, label: "Group" } }
    outputs: Record<string, { name: string; value: string; type: string; group_index: number; label: string }>;

    // Optional execution state
    status?: "executed" | "failed" | "not_executed";
    error?: string | null;

    // Optional hover handlers
    onMouseEnter?: () => void;
    onMouseLeave?: () => void;

    // Optional highlight state (for cross-component highlighting)
    isHighlighted?: boolean;
  };
}

export function ExecutedModule({ data }: ExecutedModuleProps) {
  const {
    moduleId,
    moduleName,
    moduleColor,
    inputs,
    outputs,
    status = "not_executed",
    error,
    onMouseEnter,
    onMouseLeave,
    isHighlighted = false,
  } = data;

  // Determine border color based on execution status and highlight state
  const getBorderColor = () => {
    if (isHighlighted) return "border-blue-400";
    if (status === "not_executed") return "border-gray-700";
    return "border-gray-600"; // executed or failed (error shown in body)
  };

  const inputEntries = Object.entries(inputs || {});
  const outputEntries = Object.entries(outputs || {});
  const hasInputs = inputEntries.length > 0;
  const hasOutputs = outputEntries.length > 0;

  return (
    <div
      className={`bg-gray-800 rounded-lg border-2 ${getBorderColor()} ${
        hasInputs && hasOutputs ? "min-w-[400px] max-w-[500px]" : "min-w-[200px] max-w-[300px]"
      } ${status === "not_executed" ? "opacity-50" : ""} transition-all duration-150`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        pointerEvents: "auto",
        boxShadow: isHighlighted ? "0 0 12px rgba(96, 165, 250, 0.6)" : undefined,
      }}
    >
      <ExecutedModuleHeader
        moduleId={moduleId}
        moduleName={moduleName}
        moduleColor={moduleColor}
      />

      <ExecutedModuleBody
        inputs={inputs}
        outputs={outputs}
        error={error}
      />
    </div>
  );
}
