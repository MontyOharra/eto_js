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
  typeVarManager: TypeVariableManager,
  moduleInstance?: ModuleInstance
): NodePin {
  const nodeId = generateUniqueId('N');
  const defaultType = getDefaultTypeForSpec(nodeSpec, typeVarManager, moduleInstance);

  const node: NodePin = {
    node_id: nodeId,
    direction,
    type: defaultType,
    name: '', // Start blank, user must fill in
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
  typeVarManager: TypeVariableManager,
  moduleInstance?: ModuleInstance
): NodePin {
  const nodeId = generateUniqueId('N');
  const defaultType = getDefaultTypeForSpec(nodeSpec, typeVarManager, moduleInstance);

  const node: NodePin = {
    node_id: nodeId,
    direction,
    type: defaultType,
    name: '', // Start blank, user must fill in
    label: nodeSpec.label,
    position_index: positionIndex,
    group_key: groupKey,
    is_static: false,
    type_var: nodeSpec.typing.type_var
  };

  typeVarManager.registerNode(nodeId, nodeSpec.typing.type_var);
  return node;
}

function getDefaultTypeForSpec(nodeSpec: NodeSpec, typeVarManager: TypeVariableManager, moduleInstance?: ModuleInstance): string {
  // Check if type variable is already assigned
  if (nodeSpec.typing.type_var) {
    const existingType = typeVarManager.getTypeVar(nodeSpec.typing.type_var);
    if (existingType) return existingType;

    // If not found in typeVarManager, check existing nodes in the module for the current TypeVar value
    if (moduleInstance) {
      const allNodes = [...moduleInstance.inputs, ...moduleInstance.outputs];
      const existingTypeVarNode = allNodes.find(node => node.type_var === nodeSpec.typing.type_var);
      if (existingTypeVarNode) {
        // Set the TypeVar in the manager and return the found type
        typeVarManager.setTypeVar(nodeSpec.typing.type_var, existingTypeVarNode.type);
        return existingTypeVarNode.type;
      }
    }
  }

  // Use first allowed type
  if (nodeSpec.typing.allowed_types && nodeSpec.typing.allowed_types.length > 0) {
    return nodeSpec.typing.allowed_types[0];
  }

  return 'str'; // fallback
}

// Main module generation
export function generateInitialNodeGroup(
  ioSide: IOSideShape,
  direction: 'in' | 'out',
  typeVarManager: TypeVariableManager
): { static: NodePin[], dynamic: NodePin[] } {
  const staticNodes: NodePin[] = [];
  const dynamicNodes: NodePin[] = [];

  // Generate static nodes
  if (ioSide.static) {
    ioSide.static.slots.forEach((nodeSpec, index) => {
      staticNodes.push(createStaticNode(nodeSpec, direction, index, typeVarManager));
    });
  }

  // Generate minimum dynamic nodes for each group
  if (ioSide.dynamic) {
    for (const group of ioSide.dynamic.groups) {
      const groupKey = group.item.label; // Use label as group identifier
      for (let i = 0; i < group.min_count; i++) {
        const positionIndex = i; // Position within this specific group
        dynamicNodes.push(createDynamicNode(group.item, direction, positionIndex, groupKey, i, typeVarManager));
      }
    }
  }

  return { static: staticNodes, dynamic: dynamicNodes };
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

  // Generate initial NodeGroups
  const inputs = generateInitialNodeGroup(template.meta.io_shape.inputs, 'in', typeVarManager);
  const outputs = generateInitialNodeGroup(template.meta.io_shape.outputs, 'out', typeVarManager);

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
  currentNodes: { static: NodePin[], dynamic: NodePin[] } | NodePin[],
  groupKey: string,
  ioSide: IOSideShape
): boolean {
  const group = ioSide.dynamic?.groups.find(g => g.item.label === groupKey);
  if (!group) return false;

  // Handle both NodeGroup structure and array format
  const allNodes = Array.isArray(currentNodes) ?
    currentNodes :
    [...(currentNodes.static || []), ...(currentNodes.dynamic || [])];

  const currentGroupCount = allNodes.filter(n => n.group_key === groupKey).length;

  return group.max_count === undefined || group.max_count === null || currentGroupCount < group.max_count;
}

export function canRemoveNodeFromGroup(
  currentNodes: { static: NodePin[], dynamic: NodePin[] } | NodePin[],
  groupKey: string,
  ioSide: IOSideShape
): boolean {
  const group = ioSide.dynamic?.groups.find(g => g.item.label === groupKey);
  if (!group) return false;

  // Handle both NodeGroup structure and array format
  const allNodes = Array.isArray(currentNodes) ?
    currentNodes :
    [...(currentNodes.static || []), ...(currentNodes.dynamic || [])];

  const currentGroupCount = allNodes.filter(n => n.group_key === groupKey).length;

  return currentGroupCount > group.min_count;
}

export function getAvailableTypesForNode(
  nodePin: NodePin,
  template: ModuleTemplate
): string[] {
  // Define all possible types (Python type names)
  const ALL_TYPES = ['str', 'int', 'float', 'bool', 'datetime'];

  if (nodePin.type_var) {
    const domain = template.meta.io_shape.type_params[nodePin.type_var];
    if (!domain || domain.length === 0) {
      return ALL_TYPES; // Empty domain means all types allowed
    }
    return domain;
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

  const allowedTypes = nodeSpec?.typing.allowed_types;

  // Empty array means all types are allowed
  if (!allowedTypes || allowedTypes.length === 0) {
    return ALL_TYPES;
  }
  return allowedTypes;
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

  // Handle NodeGroup structure
  const allNodes = [...(nodesArray.static || []), ...(nodesArray.dynamic || [])];

  // Find current group instance count
  const groupNodes = allNodes.filter(n => n.group_key === groupKey);
  const instanceIndex = groupNodes.length;

  // Find position index within the dynamic group
  const positionIndex = nodesArray.dynamic ? nodesArray.dynamic.filter(n => n.group_key === groupKey).length : 0;

  const newNode = createDynamicNode(
    group.item,
    direction === 'input' ? 'in' : 'out',
    positionIndex,
    groupKey,
    instanceIndex,
    typeVarManager,
    moduleInstance
  );

  // Add to dynamic array
  if (nodesArray.dynamic) {
    nodesArray.dynamic.push(newNode);
  } else {
    // This shouldn't happen with proper NodeGroup structure, but handle it
    console.error('Dynamic array not found in NodeGroup structure');
  }
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

  // Don't rename nodes - names are user-editable and should be preserved

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