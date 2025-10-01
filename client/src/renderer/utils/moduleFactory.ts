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
 * Generate initial nodes based on IOSideShape definition
 */
function generateInitialNodes(ioSide: IOSideShape, direction: 'in' | 'out'): NodePin[] {
  const nodes: NodePin[] = [];

  // Handle static nodes
  if (ioSide.static) {
    ioSide.static.slots.forEach((nodeSpec, index) => {
      const nodeType = getDefaultTypeFromNodeSpec(nodeSpec);
      nodes.push({
        node_id: generateUniqueId('N'),
        direction,
        type: nodeType,
        name: nodeSpec.label,
        position_index: index
      });
    });
  }

  // Handle dynamic nodes
  if (ioSide.dynamic) {
    let currentIndex = nodes.length; // Continue from where static nodes ended

    ioSide.dynamic.groups.forEach((group) => {
      const minCount = group.min_count || 0;

      // Create minimum required nodes for this group
      for (let i = 0; i < minCount; i++) {
        const nodeType = getDefaultTypeFromNodeSpec(group.item);
        nodes.push({
          node_id: generateUniqueId('N'),
          direction,
          type: nodeType,
          name: `${group.item.label}_${i + 1}`,
          position_index: currentIndex++
        });
      }
    });
  }

  return nodes;
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

  // Generate initial nodes based on new IOShape meta structure
  const inputs = generateInitialNodes(template.meta.io_shape.inputs, 'in');
  const outputs = generateInitialNodes(template.meta.io_shape.outputs, 'out');

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
export function canAddNode(currentCount: number, ioSide: IOSideShape): boolean {
  if (!ioSide) {
    console.error('canAddNode: ioSide is undefined');
    return false;
  }
  if (!ioSide.dynamic) return false;

  const groups = Object.values(ioSide.dynamic.groups);
  if (groups.length === 0) return false;

  // For simplicity, check the first dynamic group
  const group = groups[0];
  if (group.min_count === group.max_count) return false;
  if (group.max_count === null || group.max_count === undefined) return true;

  // Count only dynamic nodes (subtract static nodes if any)
  const staticCount = ioSide.static ? ioSide.static.slots.length : 0;
  const dynamicCount = currentCount - staticCount;

  return dynamicCount < group.max_count;
}

/**
 * Check if can remove nodes from a dynamic group
 */
export function canRemoveNode(currentCount: number, ioSide: IOSideShape): boolean {
  if (!ioSide) {
    console.error('canRemoveNode: ioSide is undefined');
    return false;
  }
  if (!ioSide.dynamic) return false;

  const groups = Object.values(ioSide.dynamic.groups);
  if (groups.length === 0) return false;

  // For simplicity, check the first dynamic group
  const group = groups[0];
  if (group.min_count === group.max_count) return false;

  // Count only dynamic nodes (subtract static nodes if any)
  const staticCount = ioSide.static ? ioSide.static.slots.length : 0;
  const dynamicCount = currentCount - staticCount;

  return dynamicCount > group.min_count;
}

/**
 * Add a new node to a module
 */
export function addNodeToModule(
  module: ModuleInstance,
  nodeType: 'input' | 'output',
  ioSide: IOSideShape
): NodePin | null {
  if (!ioSide) {
    console.error('addNodeToModule: ioSide is undefined');
    return null;
  }

  const nodesArray = nodeType === 'input' ? module.inputs : module.outputs;

  if (!canAddNode(nodesArray.length, ioSide)) {
    return null;
  }

  // Get the dynamic group template
  if (!ioSide.dynamic) return null;
  const groups = Object.values(ioSide.dynamic.groups);
  if (groups.length === 0) return null;

  const group = groups[0]; // Use first group for simplicity
  const defaultType = getDefaultTypeFromNodeSpec(group.item);

  const newNode: NodePin = {
    node_id: generateUniqueId('N'),
    direction: nodeType === 'input' ? 'in' : 'out',
    type: defaultType,
    name: `${group.item.label}_${nodesArray.length + 1}`,
    position_index: nodesArray.length
  };

  nodesArray.push(newNode);
  return newNode;
}

/**
 * Remove a node from a module and re-index
 */
export function removeNodeFromModule(
  module: ModuleInstance,
  nodeType: 'input' | 'output',
  nodeIndex: number,
  ioSide: IOSideShape
): string | null {
  const nodesArray = nodeType === 'input' ? module.inputs : module.outputs;

  if (!canRemoveNode(nodesArray.length, ioSide)) {
    return null;
  }

  if (nodeIndex < 0 || nodeIndex >= nodesArray.length) {
    return null;
  }

  // Remove the node
  const [removedNode] = nodesArray.splice(nodeIndex, 1);

  // Re-index remaining nodes
  nodesArray.forEach((node, idx) => {
    node.position_index = idx;
    // Optionally update names to stay sequential
    node.name = `${nodeType}_${idx + 1}`;
  });

  return removedNode.node_id;
}

/**
 * Update node type
 */
export function updateNodeType(
  module: ModuleInstance,
  nodeType: 'input' | 'output',
  nodeIndex: number,
  newType: string
): void {
  const nodesArray = nodeType === 'input' ? module.inputs : module.outputs;

  if (nodeIndex >= 0 && nodeIndex < nodesArray.length) {
    nodesArray[nodeIndex].type = newType;
  }
}