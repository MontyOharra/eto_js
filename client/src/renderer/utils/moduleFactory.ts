/**
 * Factory functions for creating module instances from templates
 */

import { generateUniqueId } from './idGenerator';

// Type definitions for the new structure
export interface NodePin {
  node_id: string;
  direction: 'in' | 'out';
  type: string;
  name: string;
  position_index: number;
}

export interface ModuleInstance {
  module_instance_id: string;
  module_ref: string;
  module_kind: string;
  config: Record<string, any>;
  inputs: NodePin[];
  outputs: NodePin[];
}

export interface MetaDefinition {
  allow: boolean;
  min_count: number;
  max_count: number | null;
  type: string[];  // Array of allowed types - empty array means all types allowed
}

/**
 * Get the default type from a meta type definition
 */
function getDefaultType(metaType: string[]): string {
  // If empty array, default to string
  if (metaType.length === 0) {
    return 'string';
  }
  // Use first allowed type as default
  return mapPythonTypeToJs(metaType[0]);
}

/**
 * Check if a meta definition allows variable types
 */
export function hasVariableTypes(metaType: string[]): boolean {
  // Variable if array has more than one element or is empty (all types)
  return metaType.length !== 1;
}

/**
 * Get allowed types from meta definition
 */
export function getAllowedTypes(metaType: string[]): string[] {
  // If empty array, return all scalar types
  if (metaType.length === 0) {
    return ['string', 'number', 'boolean', 'datetime'];
  }
  // Otherwise return the mapped array
  return metaType.map(mapPythonTypeToJs);
}

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
 * Generate initial nodes based on meta constraints
 */
function generateInitialNodes(meta: MetaDefinition, direction: 'in' | 'out'): NodePin[] {
  const nodes: NodePin[] = [];

  // Determine initial count
  let count: number;
  if (!meta.allow) {
    // Static nodes - use min_count (or 1 if not specified)
    count = meta.min_count || 1;
  } else {
    // Dynamic nodes - start with minimum
    count = meta.min_count || 0;
  }

  // Create nodes
  for (let i = 0; i < count; i++) {
    nodes.push({
      node_id: generateUniqueId('N'),
      direction,
      type: getDefaultType(meta.type),
      name: `${direction === 'in' ? 'input' : 'output'}_${i + 1}`,
      position_index: i
    });
  }

  return nodes;
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
export function createModuleInstance(template: any, position: { x: number; y: number }): ModuleInstance {
  const moduleId = generateUniqueId('M');

  // Initialize config from schema defaults
  const config = initializeConfig(template.config_schema);

  // Generate initial nodes based on meta
  const inputs = generateInitialNodes(template.meta.inputs, 'in');
  const outputs = generateInitialNodes(template.meta.outputs, 'out');

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
export function isNodeSideStatic(meta: MetaDefinition): boolean {
  return !meta.allow || meta.min_count === meta.max_count;
}

/**
 * Check if can add more nodes
 */
export function canAddNode(currentCount: number, meta: MetaDefinition): boolean {
  if (!meta.allow) return false;
  if (meta.min_count === meta.max_count) return false;
  if (meta.max_count === null) return true;
  return currentCount < meta.max_count;
}

/**
 * Check if can remove nodes
 */
export function canRemoveNode(currentCount: number, meta: MetaDefinition): boolean {
  if (!meta.allow) return false;
  if (meta.min_count === meta.max_count) return false;
  return currentCount > meta.min_count;
}

/**
 * Add a new node to a module
 */
export function addNodeToModule(
  module: ModuleInstance,
  nodeType: 'input' | 'output',
  meta: MetaDefinition
): NodePin | null {
  const nodesArray = nodeType === 'input' ? module.inputs : module.outputs;

  if (!canAddNode(nodesArray.length, meta)) {
    return null;
  }

  const newNode: NodePin = {
    node_id: generateUniqueId('N'),
    direction: nodeType === 'input' ? 'in' : 'out',
    type: getDefaultType(meta.type),
    name: `${nodeType}_${nodesArray.length + 1}`,
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
  meta: MetaDefinition
): string | null {
  const nodesArray = nodeType === 'input' ? module.inputs : module.outputs;

  if (!canRemoveNode(nodesArray.length, meta)) {
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