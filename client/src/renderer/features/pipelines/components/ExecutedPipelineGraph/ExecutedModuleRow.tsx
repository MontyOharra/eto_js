/**
 * ExecutedModuleRow
 * Displays an individual input or output pin row for executed modules
 * Read-only version of NodeRow for execution visualization
 */

import { Handle, Position } from "@xyflow/react";
import { TYPE_COLORS } from "../../utils/moduleUtils";

interface ExecutedModuleRowProps {
  nodeId: string;
  name: string;
  type: string;
  value: string;
  direction: "input" | "output";
}

export function ExecutedModuleRow({
  nodeId,
  name,
  type,
  direction,
}: ExecutedModuleRowProps) {
  const handleColor = TYPE_COLORS[type] || "#6B7280";

  return (
    <div className="relative flex items-center gap-2 py-1.5">
      {/* Connection Handle - Centered on outer edge */}
      <Handle
        type={direction === "input" ? "target" : "source"}
        position={direction === "input" ? Position.Left : Position.Right}
        id={nodeId}
        className="!w-5 !h-5 !border-3 !border-gray-900"
        style={{
          [direction === "input" ? "left" : "right"]: -13,
          backgroundColor: handleColor,
        }}
      />

      {/* Node Content - Centered layout */}
      <div className="flex items-center w-full">
        <div className="flex-1 min-w-0 nodrag flex items-center">
          <div className="text-sm text-gray-300 px-1.5 py-0.5 w-full min-h-[24px] text-center break-words">
            {name}
          </div>
        </div>
      </div>
    </div>
  );
}
