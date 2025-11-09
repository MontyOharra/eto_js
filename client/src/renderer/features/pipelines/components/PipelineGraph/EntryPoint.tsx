import { Module } from "./Module";
import { ModuleInstance, EntryPoint as EntryPointType } from "../../types";
import { ENTRY_POINT_TEMPLATE } from "../../utils/moduleFactory";


export interface EntryPointProps {
  data: {
    // Core data (always required)
    entryPoint: EntryPointType;

    onHandleClick?: (
      nodeId: string,
      handleId: string,
      handleType: "source" | "target"
    ) => void;

    // Interaction callbacks (optional)
    onModuleMouseEnter?: (moduleId: string) => void;
    onModuleMouseLeave?: () => void;
  };
}

// ============================================================================
// EntryPoint Component
// ============================================================================

export function EntryPoint({ data }: EntryPointProps) {
  const { entryPoint, onHandleClick, onModuleMouseEnter, onModuleMouseLeave } = data;

  // Create synthetic ModuleInstance from EntryPoint
  const moduleInstance: ModuleInstance = {
    module_instance_id: entryPoint.entry_point_id,
    module_ref: "entry_point:1.0.0", // Synthetic module reference
    config: {},
    inputs: [], // Entry points have no inputs
    outputs: entryPoint.outputs, // Use the actual outputs from EntryPoint
  };

  // Pass through to Module component with synthetic data
  return (
    <Module
      data={{
        moduleInstance,
        template: ENTRY_POINT_TEMPLATE,
        onHandleClick,
        // Pass through interaction callbacks
        onModuleMouseEnter,
        onModuleMouseLeave,
        // Edit callbacks are intentionally omitted - entry points are not editable in the same way
        // (no delete, no add/remove nodes, no config)
      }}
    />
  );
}
