/**
 * Factory functions for creating module instances from templates
 */

import { generateUniqueId } from './idGenerator';

// Import types from the main types file
import type {
  NodePin,
  ModuleInstance,
  ModuleTemplate,
  IOSideShape,
  StaticNodes,
  DynamicNodes,
  NodeSpec
} from '../types/pipelineTypes';

// Removed getDefaultType - replaced with getDefaultTypeFromNodeSpec

// Removed hasVariableTypes and getAllowedTypes - no longer needed with IOShape structure

/**
 * Map Python type names to JavaScript/frontend type names
 */
function mapPythonTypeToJs(pythonType: string): string {
  const typeMap: Record<string, string> = {
    'str': 'string',
    'int': 'number',
    'float': 'number',
    'bool': 'boolean',
    'datetime': 'datetime',
  };
  return typeMap[pythonType] || pythonType;
}

/**
 * Get default value for a config property type
 */
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

/**
 * Generate initial NodeGroup based on IOSideShape definition
 */
function generateInitialNodeGroup(ioSide: IOSideShape, direction: 'in' | 'out'): { static: NodePin[], dynamic: NodePin[] } {
  const staticNodes: NodePin[] = [];
  const dynamicNodes: NodePin[] = [];

  // Handle static nodes
  if (ioSide.static) {
    ioSide.static.slots.forEach((nodeSpec, index) => {
      const nodeType = getDefaultTypeFromNodeSpec(nodeSpec);
      staticNodes.push({
        node_id: generateUniqueId('N'),
        direction,
        type: nodeType,
        name: `${nodeSpec.label}_${index + 1}`,
        position_index: index
      });
    });
  }

  // Handle dynamic nodes
  if (ioSide.dynamic) {
    ioSide.dynamic.groups.forEach((group) => {
      const minCount = group.min_count || 0;

      // Create minimum required nodes for this group
      for (let i = 0; i < minCount; i++) {
        const nodeType = getDefaultTypeFromNodeSpec(group.item);
        dynamicNodes.push({
          node_id: generateUniqueId('N'),
          direction,
          type: nodeType,
          name: `${group.item.label}_${i + 1}`,
          position_index: i,
          group_key: group.item.label // Add group_key for dynamic nodes
        });
      }
    });
  }

  return { static: staticNodes, dynamic: dynamicNodes };
}

/**
 * Get the default type from a NodeSpec
 */
function getDefaultTypeFromNodeSpec(nodeSpec: NodeSpec): string {
  if (nodeSpec.typing.allowed_types && nodeSpec.typing.allowed_types.length > 0) {
    return mapPythonTypeToJs(nodeSpec.typing.allowed_types[0]);
  }
  return 'string'; // Default fallback
}

/**
 * Check if an IOSideShape allows variable types for the first node/group
 */
export function hasVariableTypes(ioSide: IOSideShape): boolean {
  // Check static nodes first
  if (ioSide.static && ioSide.static.slots.length > 0) {
    const firstSlot = ioSide.static.slots[0];
    const allowedTypes = firstSlot.typing.allowed_types || [];
    return allowedTypes.length !== 1;
  }

  // Check dynamic nodes
  if (ioSide.dynamic) {
    const groups = Object.values(ioSide.dynamic.groups);
    if (groups.length > 0) {
      const firstGroup = groups[0];
      const allowedTypes = firstGroup.item.typing.allowed_types || [];
      return allowedTypes.length !== 1;
    }
  }

  return false;
}

/**
 * Get allowed types for the first node/group in an IOSideShape
 */
export function getAllowedTypes(ioSide: IOSideShape): string[] {
  // Check static nodes first
  if (ioSide.static && ioSide.static.slots.length > 0) {
    const firstSlot = ioSide.static.slots[0];
    const allowedTypes = firstSlot.typing.allowed_types || [];
    if (allowedTypes.length === 0) {
      return ['string', 'number', 'boolean', 'datetime']; // All types
    }
    return allowedTypes.map(mapPythonTypeToJs);
  }

  // Check dynamic nodes
  if (ioSide.dynamic) {
    const groups = Object.values(ioSide.dynamic.groups);
    if (groups.length > 0) {
      const firstGroup = groups[0];
      const allowedTypes = firstGroup.item.typing.allowed_types || [];
      if (allowedTypes.length === 0) {
        return ['string', 'number', 'boolean', 'datetime']; // All types
      }
      return allowedTypes.map(mapPythonTypeToJs);
    }
  }

  return ['string']; // Default fallback
}

/**
 * Initialize config from schema with defaults
 */
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

/**
 * Create a new module instance from a template
 */
export function createModuleInstance(template: ModuleTemplate, position: { x: number; y: number }): ModuleInstance {
  const moduleId = generateUniqueId('M');

  // Initialize config from schema defaults
  const config = initializeConfig(template.config_schema);

  // Generate initial NodeGroups based on new IOShape meta structure
  const inputs = generateInitialNodeGroup(template.meta.io_shape.inputs, 'in');
  const outputs = generateInitialNodeGroup(template.meta.io_shape.outputs, 'out');

  return {
    module_instance_id: moduleId,
    module_ref: `${template.id}:${template.version || '1.0.0'}`,
    module_kind: template.kind || 'transform',
    config,
    inputs,
    outputs
  };
}

/**
 * Check if nodes are static (cannot add/remove)
 */
export function isNodeSideStatic(ioSide: IOSideShape): boolean {
  // If only static nodes exist, it's static
  if (ioSide.static && !ioSide.dynamic) return true;

  // If only dynamic nodes exist, check if they can be modified
  if (!ioSide.static && ioSide.dynamic) {
    const groups = Object.values(ioSide.dynamic.groups);
    return groups.every(group => group.min_count === group.max_count);
  }

  // Mixed static/dynamic: dynamic part determines if we can add/remove
  if (ioSide.dynamic) {
    const groups = Object.values(ioSide.dynamic.groups);
    return groups.every(group => group.min_count === group.max_count);
  }

  return true; // Default to static if no clear dynamic behavior
}

/**
 * Check if can add more nodes to a dynamic group
 */
export function canAddNode(nodeGroup: { static: NodePin[], dynamic: NodePin[] }, ioSide: IOSideShape, groupId?: string): boolean {
  if (!ioSide) {
    console.error('canAddNode: ioSide is undefined');
    return false;
  }
  if (!ioSide.dynamic) return false;

  const groups = ioSide.dynamic.groups;
  if (groups.length === 0) return false;

  // Find the specific group or use the first one
  const group = groupId ?
    groups.find(g => g.item.label === groupId) || groups[0] :
    groups[0];

  if (group.min_count === group.max_count) return false;
  if (group.max_count === null || group.max_count === undefined) return true;

  // Count only dynamic nodes in this specific group
  const dynamicNodesInGroup = nodeGroup.dynamic.filter(n => n.group_key === group.item.label);

  return dynamicNodesInGroup.length < group.max_count;
}

/**
 * Check if can remove nodes from a dynamic group
 */
export function canRemoveNode(nodeGroup: { static: NodePin[], dynamic: NodePin[] }, ioSide: IOSideShape, groupId?: string): boolean {
  if (!ioSide) {
    console.error('canRemoveNode: ioSide is undefined');
    return false;
  }
  if (!ioSide.dynamic) return false;

  const groups = ioSide.dynamic.groups;
  if (groups.length === 0) return false;

  // Find the specific group or use the first one
  const group = groupId ?
    groups.find(g => g.item.label === groupId) || groups[0] :
    groups[0];

  if (group.min_count === group.max_count) return false;

  // Count only dynamic nodes in this specific group
  const dynamicNodesInGroup = nodeGroup.dynamic.filter(n => n.group_key === group.item.label);

  return dynamicNodesInGroup.length > group.min_count;
}

/**
 * Add a new node to a module (works with NodeGroup structure)
 */
export function addNodeToModule(
  module: ModuleInstance,
  nodeType: 'input' | 'output',
  ioSide: IOSideShape,
  groupId?: string
): NodePin | null {
  if (!ioSide) {
    console.error('addNodeToModule: ioSide is undefined');
    return null;
  }

  const nodeGroup = nodeType === 'input' ? module.inputs : module.outputs;

  if (!canAddNode(nodeGroup, ioSide, groupId)) {
    return null;
  }

  // Get the dynamic group template
  if (!ioSide.dynamic) return null;
  const groups = ioSide.dynamic.groups;
  if (groups.length === 0) return null;

  // Find the specific group or use the first one
  const group = groupId ?
    groups.find(g => g.item.label === groupId) || groups[0] :
    groups[0];

  const defaultType = getDefaultTypeFromNodeSpec(group.item);
  const dynamicNodesInGroup = nodeGroup.dynamic.filter(n => n.group_key === group.item.label);

  const newNode: NodePin = {
    node_id: generateUniqueId('N'),
    direction: nodeType === 'input' ? 'in' : 'out',
    type: defaultType,
    name: `${group.item.label}_${dynamicNodesInGroup.length + 1}`,
    position_index: dynamicNodesInGroup.length,
    group_key: group.item.label
  };

  nodeGroup.dynamic.push(newNode);
  return newNode;
}

/**
 * Remove a node from a module and re-index (works with NodeGroup structure)
 */
export function removeNodeFromModule(
  module: ModuleInstance,
  nodeType: 'input' | 'output',
  nodeId: string,
  ioSide: IOSideShape
): string | null {
  const nodeGroup = nodeType === 'input' ? module.inputs : module.outputs;

  if (!canRemoveNode(nodeGroup, ioSide)) {
    return null;
  }

  // Find and remove the node from dynamic array (static nodes can't be removed)
  const nodeIndex = nodeGroup.dynamic.findIndex(n => n.node_id === nodeId);
  if (nodeIndex === -1) {
    return null; // Node not found or trying to remove static node
  }

  // Remove the node
  const [removedNode] = nodeGroup.dynamic.splice(nodeIndex, 1);

  // Re-index remaining dynamic nodes in the same group
  const groupKey = removedNode.group_key;
  if (groupKey) {
    const sameGroupNodes = nodeGroup.dynamic.filter(n => n.group_key === groupKey);
    sameGroupNodes.forEach((node, idx) => {
      node.position_index = idx;
      node.name = `${groupKey}_${idx + 1}`;
    });
  }

  return removedNode.node_id;
}

/**
 * Update node type (works with NodeGroup structure)
 */
export function updateNodeType(
  module: ModuleInstance,
  nodeType: 'input' | 'output',
  nodeId: string,
  newType: string
): void {
  const nodeGroup = nodeType === 'input' ? module.inputs : module.outputs;

  // Check static nodes first
  const staticNode = nodeGroup.static.find(n => n.node_id === nodeId);
  if (staticNode) {
    staticNode.type = newType;
    return;
  }

  // Check dynamic nodes
  const dynamicNode = nodeGroup.dynamic.find(n => n.node_id === nodeId);
  if (dynamicNode) {
    dynamicNode.type = newType;
  }
}