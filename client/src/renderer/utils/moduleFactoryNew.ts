/**
 * New module factory supporting static/dynamic nodes and type variables
 * Replaces the old moduleFactory.ts system
 */

import {
  ModuleTemplate,
  NodePin,
  IOSideShape,
  DynamicNodeGroup,
  NodeSpec,
  NodeTypeRule,
  ModuleInstance,
  TypeVariableState,
  DynamicGroupInfo
} from '../types/moduleTypes';
import { generateUniqueId } from './idGenerator';

// Type variable management class
export class TypeVariableManager {
  private state: TypeVariableState;

  constructor() {
    this.state = {
      assignments: {},
      affectedNodes: {}
    };
  }

  setTypeVar(typeVar: string, type: string): string[] {
    this.state.assignments[typeVar] = type;
    return this.state.affectedNodes[typeVar] || [];
  }

  getTypeVar(typeVar: string): string | undefined {
    return this.state.assignments[typeVar];
  }

  registerNode(nodeId: string, typeVar?: string): void {
    if (typeVar) {
      if (!this.state.affectedNodes[typeVar]) {
        this.state.affectedNodes[typeVar] = [];
      }
      this.state.affectedNodes[typeVar].push(nodeId);
    }
  }

  unregisterNode(nodeId: string): void {
    Object.keys(this.state.affectedNodes).forEach(typeVar => {
      this.state.affectedNodes[typeVar] = this.state.affectedNodes[typeVar].filter(id => id !== nodeId);
    });
  }

  getState(): TypeVariableState {
    return { ...this.state };
  }
}

// Node generation functions
function createStaticNode(
  nodeSpec: NodeSpec,
  direction: 'in' | 'out',
  positionIndex: number,
  typeVarManager: TypeVariableManager
): NodePin {
  const nodeId = generateUniqueId('N');
  const defaultType = getDefaultTypeForSpec(nodeSpec, typeVarManager);

  const node: NodePin = {
    node_id: nodeId,
    direction,
    type: defaultType,
    name: `${nodeSpec.label}_${positionIndex + 1}`, // Default name based on label
    label: nodeSpec.label,
    position_index: positionIndex,
    is_static: true,
    type_var: nodeSpec.typing.type_var
  };

  typeVarManager.registerNode(nodeId, nodeSpec.typing.type_var);
  return node;
}

function createDynamicNode(
  nodeSpec: NodeSpec,
  direction: 'in' | 'out',
  positionIndex: number,
  groupKey: string,
  instanceIndex: number,
  typeVarManager: TypeVariableManager
): NodePin {
  const nodeId = generateUniqueId('N');
  const defaultType = getDefaultTypeForSpec(nodeSpec, typeVarManager);

  const node: NodePin = {
    node_id: nodeId,
    direction,
    type: defaultType,
    name: `${nodeSpec.label}_${instanceIndex + 1}`,
    label: nodeSpec.label,
    position_index: positionIndex,
    group_key: groupKey,
    is_static: false,
    type_var: nodeSpec.typing.type_var
  };

  typeVarManager.registerNode(nodeId, nodeSpec.typing.type_var);
  return node;
}

function getDefaultTypeForSpec(nodeSpec: NodeSpec, typeVarManager: TypeVariableManager): string {
  // Check if type variable is already assigned
  if (nodeSpec.typing.type_var) {
    const existingType = typeVarManager.getTypeVar(nodeSpec.typing.type_var);
    if (existingType) return existingType;
  }

  // Use first allowed type
  if (nodeSpec.typing.allowed_types && nodeSpec.typing.allowed_types.length > 0) {
    return nodeSpec.typing.allowed_types[0];
  }

  return 'string'; // fallback
}

// Main module generation
export function generateInitialNodes(
  ioSide: IOSideShape,
  direction: 'in' | 'out',
  typeVarManager: TypeVariableManager
): NodePin[] {
  const nodes: NodePin[] = [];
  let positionIndex = 0;

  // Generate static nodes first
  if (ioSide.static) {
    for (const nodeSpec of ioSide.static.slots) {
      nodes.push(createStaticNode(nodeSpec, direction, positionIndex, typeVarManager));
      positionIndex++;
    }
  }

  // Generate minimum dynamic nodes for each group
  if (ioSide.dynamic) {
    for (const group of ioSide.dynamic.groups) {
      const groupKey = group.item.label; // Use label as group identifier
      for (let i = 0; i < group.min_count; i++) {
        nodes.push(createDynamicNode(group.item, direction, positionIndex, groupKey, i, typeVarManager));
        positionIndex++;
      }
    }
  }

  return nodes;
}

// Initialize config from schema with defaults
function initializeConfig(configSchema: any): Record<string, any> {
  const config: Record<string, any> = {};

  if (configSchema?.properties) {
    for (const [key, prop] of Object.entries(configSchema.properties)) {
      const propDef = prop as any;
      if (propDef.default !== undefined) {
        config[key] = propDef.default;
      } else {
        config[key] = getDefaultForType(propDef.type);
      }
    }
  }

  return config;
}

function getDefaultForType(type: string): any {
  switch (type) {
    case 'string': return '';
    case 'number':
    case 'integer': return 0;
    case 'boolean': return false;
    case 'array': return [];
    case 'object': return {};
    default: return null;
  }
}

// Create module instance with type variable manager
export function createModuleInstance(template: ModuleTemplate, position: { x: number; y: number }) {
  const moduleId = generateUniqueId('M');
  const typeVarManager = new TypeVariableManager();

  // Initialize config from schema defaults
  const config = initializeConfig(template.config_schema);

  // Generate initial nodes
  const inputs = generateInitialNodes(template.meta.io_shape.inputs, 'in', typeVarManager);
  const outputs = generateInitialNodes(template.meta.io_shape.outputs, 'out', typeVarManager);

  const moduleInstance: ModuleInstance = {
    module_instance_id: moduleId,
    module_ref: `${template.id}:${template.version}`,
    module_kind: template.kind,
    config,
    inputs,
    outputs
  };

  return {
    moduleInstance,
    typeVarManager
  };
}

// Node management functions
export function canAddNodeToGroup(
  currentNodes: NodePin[],
  groupKey: string,
  ioSide: IOSideShape
): boolean {
  const group = ioSide.dynamic?.groups.find(g => g.item.label === groupKey);
  if (!group) return false;

  const currentGroupCount = currentNodes.filter(n => n.group_key === groupKey).length;

  return group.max_count === undefined || group.max_count === null || currentGroupCount < group.max_count;
}

export function canRemoveNodeFromGroup(
  currentNodes: NodePin[],
  groupKey: string,
  ioSide: IOSideShape
): boolean {
  const group = ioSide.dynamic?.groups.find(g => g.item.label === groupKey);
  if (!group) return false;

  const currentGroupCount = currentNodes.filter(n => n.group_key === groupKey).length;

  return currentGroupCount > group.min_count;
}

export function getAvailableTypesForNode(
  nodePin: NodePin,
  template: ModuleTemplate
): string[] {
  if (nodePin.type_var) {
    const domain = template.meta.io_shape.type_params[nodePin.type_var];
    return domain || ['string'];
  }

  // Find the node spec
  const ioSide = nodePin.direction === 'in'
    ? template.meta.io_shape.inputs
    : template.meta.io_shape.outputs;

  let nodeSpec: NodeSpec | undefined;

  if (nodePin.is_static && ioSide.static) {
    nodeSpec = ioSide.static.slots[nodePin.position_index];
  } else if (!nodePin.is_static && ioSide.dynamic && nodePin.group_key) {
    const group = ioSide.dynamic.groups.find(g => g.item.label === nodePin.group_key);
    nodeSpec = group?.item;
  }

  return nodeSpec?.typing.allowed_types || ['string'];
}

export function hasVariableTypes(nodePin: NodePin, template: ModuleTemplate): boolean {
  const availableTypes = getAvailableTypesForNode(nodePin, template);
  return availableTypes.length > 1;
}

export function isTypeVariable(nodePin: NodePin): boolean {
  return !!nodePin.type_var;
}

export function updateNodeTypeWithTypeVars(
  moduleInstance: ModuleInstance,
  nodeId: string,
  newType: string,
  typeVarManager: TypeVariableManager
): string[] {
  const allNodes = [...moduleInstance.inputs, ...moduleInstance.outputs];
  const targetNode = allNodes.find(n => n.node_id === nodeId);

  if (!targetNode) return [];

  // Update the target node
  targetNode.type = newType;

  // If it has a type variable, update all related nodes
  if (targetNode.type_var) {
    const affectedNodeIds = typeVarManager.setTypeVar(targetNode.type_var, newType);

    // Update all affected nodes
    allNodes.forEach(node => {
      if (node.type_var === targetNode.type_var && node.node_id !== nodeId) {
        node.type = newType;
      }
    });

    return affectedNodeIds.filter(id => id !== nodeId);
  }

  return [];
}

export function addNodeToGroup(
  moduleInstance: ModuleInstance,
  direction: 'input' | 'output',
  groupKey: string,
  template: ModuleTemplate,
  typeVarManager: TypeVariableManager
): NodePin | null {
  const ioSide = direction === 'input'
    ? template.meta.io_shape.inputs
    : template.meta.io_shape.outputs;

  const nodesArray = direction === 'input' ? moduleInstance.inputs : moduleInstance.outputs;

  if (!canAddNodeToGroup(nodesArray, groupKey, ioSide)) {
    return null;
  }

  const group = ioSide.dynamic?.groups.find(g => g.item.label === groupKey);
  if (!group) return null;

  // Find current group instance count
  const groupNodes = nodesArray.filter(n => n.group_key === groupKey);
  const instanceIndex = groupNodes.length;

  // Find position index (after all existing nodes)
  const positionIndex = nodesArray.length;

  const newNode = createDynamicNode(
    group.item,
    direction === 'input' ? 'in' : 'out',
    positionIndex,
    groupKey,
    instanceIndex,
    typeVarManager
  );

  nodesArray.push(newNode);
  return newNode;
}

export function removeNodeFromGroup(
  moduleInstance: ModuleInstance,
  direction: 'input' | 'output',
  nodeIndex: number,
  template: ModuleTemplate,
  typeVarManager: TypeVariableManager
): string | null {
  const ioSide = direction === 'input'
    ? template.meta.io_shape.inputs
    : template.meta.io_shape.outputs;

  const nodesArray = direction === 'input' ? moduleInstance.inputs : moduleInstance.outputs;

  if (nodeIndex < 0 || nodeIndex >= nodesArray.length) return null;

  const nodeToRemove = nodesArray[nodeIndex];

  // Can't remove static nodes
  if (nodeToRemove.is_static) return null;

  // Check if can remove from group
  if (!nodeToRemove.group_key || !canRemoveNodeFromGroup(nodesArray, nodeToRemove.group_key, ioSide)) {
    return null;
  }

  // Remove the node
  const [removedNode] = nodesArray.splice(nodeIndex, 1);

  // Unregister from type variable manager
  typeVarManager.unregisterNode(removedNode.node_id);

  // Re-index remaining nodes
  nodesArray.forEach((node, idx) => {
    node.position_index = idx;
  });

  // Re-number nodes in the same group
  const groupNodes = nodesArray.filter(n => n.group_key === nodeToRemove.group_key);
  groupNodes.forEach((node, idx) => {
    node.name = `${node.label}_${idx + 1}`;
  });

  return removedNode.node_id;
}

export function getDynamicGroupsInfo(
  moduleInstance: ModuleInstance,
  direction: 'input' | 'output',
  template: ModuleTemplate
): DynamicGroupInfo[] {
  const ioSide = direction === 'input'
    ? template.meta.io_shape.inputs
    : template.meta.io_shape.outputs;

  const nodesArray = direction === 'input' ? moduleInstance.inputs : moduleInstance.outputs;

  if (!ioSide.dynamic) return [];

  return ioSide.dynamic.groups.map((group) => {
    const groupKey = group.item.label; // Use label as group identifier
    const currentCount = nodesArray.filter(n => n.group_key === groupKey).length;

    return {
      groupKey,
      group,
      currentCount,
      canAdd: canAddNodeToGroup(nodesArray, groupKey, ioSide),
      canRemove: canRemoveNodeFromGroup(nodesArray, groupKey, ioSide)
    };
  });
}