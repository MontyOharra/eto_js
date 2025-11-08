/**
 * Module Component
 * Unified module node component for the pipeline graph
 * Displays module header with title and controls
 */

import { useState } from "react";
import { ModuleTemplate } from "../../../modules/types";
import { ModuleInstance, NodePin } from "../../types";
import { getTextColor } from "../../utils/moduleUtils";
import { ModuleBody } from "./ModuleBody";

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
  const {
    moduleInstance,
    template,
    onDeleteModule,
    onUpdateNode,
    onAddNode,
    onRemoveNode,
    onConfigChange,
    pendingConnection,
    onHandleClick,
    getEffectiveAllowedTypes,
    getConnectedOutputName,
    onTextFocus,
    onTextBlur,
    onModuleMouseEnter,
    onModuleMouseLeave,
  } = data;

  // State for type variable highlighting
  const [highlightedTypeVar, setHighlightedTypeVar] = useState<string | null>(
    null
  );

  const headerColor = template.color || "#4B5563";
  const textColor = getTextColor(headerColor);

  // Check if module has both inputs and outputs for sizing
  const hasInputs = moduleInstance.inputs.length > 0;
  const hasOutputs = moduleInstance.outputs.length > 0;
  const isSingleSided =
    (hasInputs && !hasOutputs) || (!hasInputs && hasOutputs);

  return (
    <div
      className={`bg-gray-800 rounded-lg border-2 border-gray-600 ${isSingleSided ? "min-w-[200px]" : "min-w-[400px]"} max-w-[400px] w-min`}
      style={{ pointerEvents: "auto" }}
      onMouseEnter={() =>
        onModuleMouseEnter?.(moduleInstance.module_instance_id)
      }
      onMouseLeave={() => onModuleMouseLeave?.()}
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
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-mono opacity-75"
              style={{ color: textColor }}
            >
              {moduleInstance.module_instance_id}
            </span>
            {onDeleteModule && (
              <button
                onClick={() => onDeleteModule(moduleInstance.module_instance_id)}
                className="opacity-75 hover:opacity-100 transition-opacity"
                style={{ color: textColor }}
                title="Delete module"
              >
                <svg
                  className="w-4 h-4"
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
            )}
          </div>
        </div>
      </div>

      {/* Module Body */}
      <ModuleBody
        moduleInstance={moduleInstance}
        template={template}
        onUpdateNode={onUpdateNode}
        onAddNode={onAddNode}
        onRemoveNode={onRemoveNode}
        onTextFocus={onTextFocus}
        onTextBlur={onTextBlur}
        onHandleClick={onHandleClick}
        pendingConnection={pendingConnection}
        getEffectiveAllowedTypes={getEffectiveAllowedTypes}
        getConnectedOutputName={getConnectedOutputName}
        highlightedTypeVar={highlightedTypeVar}
        onTypeVarFocus={setHighlightedTypeVar}
      />

      {/* TODO: Module Config section */}
    </div>
  );
}
