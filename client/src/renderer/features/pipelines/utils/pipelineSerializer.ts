/**
 * Serialization utilities to convert between frontend and backend pipeline formats
 */
import {
  NodePin, 
  ModuleInstance,
  PipelineState,
  VisualState,
  NodeConnection,
  EntryPoint,
} from "../types";

// Backend-compatible types (stripped of frontend-only fields)
interface BackendNodePin {
  node_id: string;
  type: string;
  name: string;
  position_index: number;
  group_index: number;
}

interface BackendEntryPoint {
  entry_point_id: string;
  name: string;
  outputs: BackendNodePin[];
}

interface BackendModuleInstance {
  module_instance_id: string;
  module_ref: string;
  config: Record<string, any>;
  inputs: BackendNodePin[];
  outputs: BackendNodePin[];
}

interface BackendPipelineState {
  entry_points: BackendEntryPoint[];
  modules: BackendModuleInstance[];
  connections: NodeConnection[];
}

export interface BackendPipelineData {
  name?: string;
  description?: string;
  pipeline_state: BackendPipelineState;
  visual_state: VisualState;
}

/**
 * Complete pipeline data serialization for backend API
 */
export function serializePipelineData(
  pipelineState: PipelineState,
  visualState: VisualState,
  name?: string,
  description?: string
): BackendPipelineData {
  // Convert NodePin to BackendNodePin (strip frontend-only fields)
  const serializeNodePin = (pin: NodePin): BackendNodePin => ({
    node_id: pin.node_id,
    type: pin.type,
    name: pin.name,
    position_index: pin.position_index,
    group_index: pin.group_index,
  });

  // Convert ModuleInstance to BackendModuleInstance
  const serializeModuleInstance = (module: ModuleInstance): BackendModuleInstance => ({
    module_instance_id: module.module_instance_id,
    module_ref: module.module_ref,
    config: module.config,
    inputs: module.inputs.map(serializeNodePin),
    outputs: module.outputs.map(serializeNodePin),
  });

  // Convert EntryPoint to BackendEntryPoint
  const serializeEntryPoint = (entryPoint: EntryPoint): BackendEntryPoint => ({
    entry_point_id: entryPoint.entry_point_id,
    name: entryPoint.name,
    outputs: entryPoint.outputs.map(serializeNodePin),
  });

  return {
    name,
    description,
    pipeline_state: {
      entry_points: pipelineState.entry_points.map(serializeEntryPoint),
      modules: pipelineState.modules.map(serializeModuleInstance),
      connections: pipelineState.connections,
    },
    visual_state: visualState,
  };
}
