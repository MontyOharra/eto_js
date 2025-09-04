/**
 * Type definitions for the transformation pipeline graph
 */

export interface NodeState {
  id: string;
  name: string; // Required name to match component interface
  type: 'string' | 'number' | 'boolean' | 'datetime';
  description: string;
  required: boolean;
}

export interface ModuleNodeState {
  inputs: NodeState[];
  outputs: NodeState[];
}

export interface PlacedModule {
  id: string;
  template: import('../../../types/modules').BaseModuleTemplate;
  position: { x: number; y: number };
  config: Record<string, unknown>;
  
  // Node state (replaces runtime inputs/outputs)
  nodes: ModuleNodeState;
}

export interface NodeConnection {
  id: string;
  fromModuleId: string;
  fromOutputIndex: number;
  toModuleId: string;
  toInputIndex: number;
}

export interface StartingConnection {
  moduleId: string;
  type: 'input' | 'output';
  index: number;
}