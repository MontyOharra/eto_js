/**
 * Module Component
 * Unified module node component for the pipeline graph
 * Displays module header with title and controls
 */

import { ModuleTemplate } from "../../../modules/types";
import { ModuleInstance, NodePin } from "../../types";
import { getTextColor } from "../../utils/moduleUtils";

// ============================================================================
// Type Definitions
// ============================================================================

interface PendingConnection {
  sourceHandleId: string;
  sourceNodeId: string;
  handleType: "source" | "target";
}

export interface ModuleProps {
  data: {
    // Core data (always required)
    moduleInstance: ModuleInstance;
    template: ModuleTemplate;

    // Edit callbacks
    onDeleteModule?: (moduleId: string) => void;
    onUpdateNode?: (
      moduleId: string,
      nodeId: string,
      updates: Partial<NodePin>
    ) => void;
    onAddNode?: (
      moduleId: string,
      direction: "input" | "output",
      groupIndex: number
    ) => void;
    onRemoveNode?: (moduleId: string, nodeId: string) => void;
    onConfigChange?: (moduleId: string, configKey: string, value: any) => void;

    // Connection management
    pendingConnection?: PendingConnection | null;
    onHandleClick?: (
      nodeId: string,
      handleId: string,
      handleType: "source" | "target"
    ) => void;

    // Type system helpers
    getEffectiveAllowedTypes?: (
      moduleId: string,
      pinId: string,
      baseAllowedTypes: string[]
    ) => string[];
    getConnectedOutputName?: (
      moduleId: string,
      inputPinId: string
    ) => string | undefined;

    // Interaction callbacks
    onTextFocus?: () => void;
    onTextBlur?: () => void;
    onModuleMouseEnter?: (moduleId: string) => void;
    onModuleMouseLeave?: () => void;
  };
}

// ============================================================================
// Module Component
// ============================================================================

export function Module({ data }: ModuleProps) {
  const { moduleInstance, template } = data;

  const headerColor = template.color || "#4B5563";
  const textColor = getTextColor(headerColor);

  return (
    <div
      className="bg-gray-800 rounded-lg border-2 border-gray-600 min-w-[400px] w-min"
      style={{ pointerEvents: "auto" }}
    >
      {/* Module Header */}
      <div
        className="px-4 py-2 rounded-t-lg border-b border-gray-600"
        style={{ backgroundColor: headerColor }}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold" style={{ color: textColor }}>
            {template.title}
          </h3>
          <span
            className="text-xs font-mono opacity-75"
            style={{ color: textColor }}
          >
            {moduleInstance.module_instance_id}
          </span>
        </div>
      </div>

      {/* Module Body - Placeholder */}
      <div className="px-4 py-2 text-gray-400 text-sm">
        Module body coming soon...
      </div>
    </div>
  );
}
