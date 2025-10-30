/**
 * Serialization utilities to convert between frontend and backend pipeline formats
 */

import { NodePin, ModuleInstance } from "../../modules/types";
import {
  PipelineState,
  VisualState,
  NodeConnection,
  EntryPoint,
  InstanceNodePin,
  BackendEntryPoint,
} from "../types";

// Backend-compatible types
export interface BackendModuleInstance {
  module_instance_id: string;
  module_ref: string;
  module_kind: string;
  config: Record<string, any>;
  inputs: InstanceNodePin[];
  outputs: InstanceNodePin[];
}

export interface BackendPipelineState {
  entry_points: BackendEntryPoint[];
  modules: BackendModuleInstance[];
  connections: NodeConnection[];
}

// Convert NodePin to InstanceNodePin (strip frontend-only fields)
export function serializeNodePin(pin: NodePin): InstanceNodePin {
  return {
    node_id: pin.node_id,
    type: pin.type,
    name: pin.name,
    position_index: pin.position_index,
    group_index: pin.group_index,
  };
}

// Convert ModuleInstance to BackendModuleInstance
export function serializeModuleInstance(
  module: ModuleInstance
): BackendModuleInstance {
  return {
    module_instance_id: module.module_instance_id,
    module_ref: module.module_ref,
    module_kind: module.module_kind,
    config: module.config,
    inputs: module.inputs.map(serializeNodePin),
    outputs: module.outputs.map(serializeNodePin),
  };
}

// Convert EntryPoint to BackendEntryPoint (strip type field)
export function serializeEntryPoint(entryPoint: EntryPoint): BackendEntryPoint {
  return {
    node_id: entryPoint.node_id,
    name: entryPoint.name,
  };
}

// Convert frontend PipelineState to backend format
export function serializePipelineState(
  state: PipelineState
): BackendPipelineState {
  return {
    entry_points: state.entry_points.map(serializeEntryPoint),
    modules: state.modules.map(serializeModuleInstance),
    connections: state.connections,
  };
}

// Visual state doesn't need conversion - it matches backend format
export function serializeVisualState(visualState: VisualState): VisualState {
  return visualState;
}

// Complete pipeline data serialization
export interface BackendPipelineData {
  name?: string;
  description?: string;
  pipeline_state: BackendPipelineState;
  visual_state: VisualState;
}

export function serializePipelineData(
  pipelineState: PipelineState,
  visualState: VisualState,
  name?: string,
  description?: string
): BackendPipelineData {
  return {
    name,
    description,
    pipeline_state: serializePipelineState(pipelineState),
    visual_state: serializeVisualState(visualState),
  };
}
