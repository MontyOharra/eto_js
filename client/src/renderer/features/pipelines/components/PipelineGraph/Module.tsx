/**
 * Module Component
 * Unified module node component for the pipeline graph
 * Displays module header with title and controls
 */

import { useState } from "react";
import { ModuleTemplate } from "../../../modules/types";
import { ModuleInstance, NodePin } from "../../types";
import { ModuleBody } from "./ModuleBody";
import { ModuleHeader } from "./ModuleHeader";
import { ModuleConfig } from "./ModuleConfig";


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
      <ModuleHeader
        moduleInstance={moduleInstance}
        template={template}
        onDeleteModule={onDeleteModule}
      />

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
        getEffectiveAllowedTypes={getEffectiveAllowedTypes}
        getConnectedOutputName={getConnectedOutputName}
        highlightedTypeVar={highlightedTypeVar}
        onTypeVarFocus={setHighlightedTypeVar}
      />

      {/* Module Config */}
      <ModuleConfig
        moduleInstance={moduleInstance}
        template={template}
        onConfigChange={onConfigChange}
      />
    </div>
  );
}
