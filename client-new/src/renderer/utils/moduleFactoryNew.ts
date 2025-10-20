/**
 * Module factory with unified NodeGroup structure
 * Creates module instances from templates
 */

import {
  ModuleTemplate,
  NodePin,
  NodeGroup,
  IOSideShape,
  ModuleInstance,
  TypeVariableState,
  GroupInfo
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

// Helper to get default type for a NodeGroup
function getDefaultType(
  group: NodeGroup,
  template: ModuleTemplate,
  typeVarManager: TypeVariableManager,
  moduleInstance?: ModuleInstance
): string {
  // Check if type variable is already assigned
  if (group.typing.type_var) {
    const existingType = typeVarManager.getTypeVar(group.typing.type_var);
    if (existingType) return existingType;

    // Check existing nodes in the module for the current TypeVar value
    if (moduleInstance) {
      const allNodes = [...moduleInstance.inputs, ...moduleInstance.outputs];
      const existingTypeVarNode = allNodes.find(node => node.type_var === group.typing.type_var);
      if (existingTypeVarNode) {
        typeVarManager.setTypeVar(group.typing.type_var, existingTypeVarNode.type);
        return existingTypeVarNode.type;
      }
    }

    // Check type_params for domain
    const domain = template.meta.io_shape.type_params[group.typing.type_var];
    if (domain && domain.length > 0) {
      return domain[0];
    }
  }

  // Use first allowed type
  if (group.typing.allowed_types && group.typing.allowed_types.length > 0) {
    return group.typing.allowed_types[0];
  }

  return 'str'; // fallback
}

// Create a single pin instance
function createPin(
  group: NodeGroup,
  groupIndex: number,
  positionIndex: number,
  direction: 'in' | 'out',
  template: ModuleTemplate,
  typeVarManager: TypeVariableManager,
  moduleInstance?: ModuleInstance
): NodePin {
  const nodeId = generateUniqueId('N');
  const defaultType = getDefaultType(group, template, typeVarManager, moduleInstance);

  // Get allowed types for this pin
  const allowedTypes = group.typing.type_var
    ? template.meta.io_shape.type_params[group.typing.type_var] || []
    : group.typing.allowed_types || [];

  const pin: NodePin = {
    node_id: nodeId,
    direction,
    type: defaultType,
    name: '',
    label: group.label,
    position_index: positionIndex,
    group_index: groupIndex,
    type_var: group.typing.type_var,
    allowed_types: allowedTypes
  };

  typeVarManager.registerNode(nodeId, group.typing.type_var);
  return pin;
}

// Generate initial pins for one side (inputs or outputs)
function generatePinsForSide(
  ioSide: IOSideShape,
  direction: 'in' | 'out',
  template: ModuleTemplate,
  typeVarManager: TypeVariableManager
): NodePin[] {
  const pins: NodePin[] = [];

  ioSide.nodes.forEach((group, groupIndex) => {
    // Create min_count pins for this group
    for (let i = 0; i < group.min_count; i++) {
      pins.push(createPin(group, groupIndex, i, direction, template, typeVarManager));
    }
  });

  return pins;
}

// Initialize config from schema with defaults
export function initializeConfig(configSchema: any): Record<string, any> {
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

export function getDefaultForType(type: string): any {
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

// Create module instance
export function createModuleInstance(template: ModuleTemplate, position: { x: number; y: number }) {
  const moduleId = generateUniqueId('M');
  const typeVarManager = new TypeVariableManager();

  const config = initializeConfig(template.config_schema);
  const inputs = generatePinsForSide(template.meta.io_shape.inputs, 'in', template, typeVarManager);
  const outputs = generatePinsForSide(template.meta.io_shape.outputs, 'out', template, typeVarManager);

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

// Group management functions
export function canAddPinToGroup(
  currentPins: NodePin[],
  groupIndex: number,
  ioSide: IOSideShape
): boolean {
  const group = ioSide.nodes[groupIndex];
  if (!group) return false;

  const currentCount = currentPins.filter(p => p.group_index === groupIndex).length;
  return group.max_count === undefined || group.max_count === null || currentCount < group.max_count;
}

export function canRemovePinFromGroup(
  currentPins: NodePin[],
  groupIndex: number,
  ioSide: IOSideShape
): boolean {
  const group = ioSide.nodes[groupIndex];
  if (!group) return false;

  const currentCount = currentPins.filter(p => p.group_index === groupIndex).length;
  return currentCount > group.min_count;
}

export function addPinToGroup(
  moduleInstance: ModuleInstance,
  direction: 'input' | 'output',
  groupIndex: number,
  template: ModuleTemplate,
  typeVarManager: TypeVariableManager
): NodePin | null {
  const ioSide = direction === 'input'
    ? template.meta.io_shape.inputs
    : template.meta.io_shape.outputs;

  const pinsArray = direction === 'input' ? moduleInstance.inputs : moduleInstance.outputs;

  if (!canAddPinToGroup(pinsArray, groupIndex, ioSide)) {
    return null;
  }

  const group = ioSide.nodes[groupIndex];
  if (!group) return null;

  // Find current position index within this group
  const groupPins = pinsArray.filter(p => p.group_index === groupIndex);
  const positionIndex = groupPins.length;

  const newPin = createPin(
    group,
    groupIndex,
    positionIndex,
    direction === 'input' ? 'in' : 'out',
    template,
    typeVarManager,
    moduleInstance
  );

  pinsArray.push(newPin);
  return newPin;
}

export function removePinFromGroup(
  moduleInstance: ModuleInstance,
  direction: 'input' | 'output',
  pinId: string,
  template: ModuleTemplate,
  typeVarManager: TypeVariableManager
): boolean {
  const ioSide = direction === 'input'
    ? template.meta.io_shape.inputs
    : template.meta.io_shape.outputs;

  const pinsArray = direction === 'input' ? moduleInstance.inputs : moduleInstance.outputs;
  const pinIndex = pinsArray.findIndex(p => p.node_id === pinId);

  if (pinIndex === -1) return false;

  const pin = pinsArray[pinIndex];
  const group = ioSide.nodes[pin.group_index];

  // Check if min_count === max_count === 1 (static node)
  if (group.min_count === 1 && group.max_count === 1) {
    return false; // Can't remove static nodes
  }

  if (!canRemovePinFromGroup(pinsArray, pin.group_index, ioSide)) {
    return false;
  }

  // Remove the pin
  pinsArray.splice(pinIndex, 1);
  typeVarManager.unregisterNode(pin.node_id);

  // Re-index position_index for pins in the same group
  pinsArray
    .filter(p => p.group_index === pin.group_index)
    .forEach((p, idx) => {
      p.position_index = idx;
    });

  return true;
}

export function getGroupsInfo(
  moduleInstance: ModuleInstance,
  direction: 'input' | 'output',
  template: ModuleTemplate
): GroupInfo[] {
  const ioSide = direction === 'input'
    ? template.meta.io_shape.inputs
    : template.meta.io_shape.outputs;

  const pinsArray = direction === 'input' ? moduleInstance.inputs : moduleInstance.outputs;

  return ioSide.nodes.map((group, groupIndex) => {
    const currentCount = pinsArray.filter(p => p.group_index === groupIndex).length;

    return {
      groupIndex,
      group,
      currentCount,
      canAdd: canAddPinToGroup(pinsArray, groupIndex, ioSide),
      canRemove: canRemovePinFromGroup(pinsArray, groupIndex, ioSide)
    };
  });
}

// Type utilities
export function getAvailableTypesForNode(
  nodePin: NodePin,
  template: ModuleTemplate
): string[] {
  const ALL_TYPES = ['str', 'int', 'float', 'bool', 'datetime'];

  if (nodePin.type_var) {
    const domain = template.meta.io_shape.type_params[nodePin.type_var];
    if (!domain || domain.length === 0) {
      return ALL_TYPES;
    }
    return domain;
  }

  const allowedTypes = nodePin.allowed_types;
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

  targetNode.type = newType;

  if (targetNode.type_var) {
    const affectedNodeIds = typeVarManager.setTypeVar(targetNode.type_var, newType);

    allNodes.forEach(node => {
      if (node.type_var === targetNode.type_var && node.node_id !== nodeId) {
        node.type = newType;
      }
    });

    return affectedNodeIds.filter(id => id !== nodeId);
  }

  return [];
}
