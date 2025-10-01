/**
 * Type constraint system for TypeVar coordination and connection validation
 */

import { ModuleInstance, ModuleTemplate, NodePin, NodeConnection } from '../types/pipelineTypes';
import { getAvailableTypesForNode } from './moduleFactoryNew';

// Type constraint information for a node
export interface NodeTypeInfo {
  nodeId: string;
  moduleId: string;
  currentType: string;
  availableTypes: string[];
  typeVar?: string;
  isTypeVar: boolean;
}

// Connection constraint result
export interface ConnectionConstraint {
  isValid: boolean;
  requiredType?: string;
  reason?: string;
}

// Type change propagation result
export interface TypeChangePropagation {
  nodesToUpdate: Array<{
    moduleId: string;
    nodeId: string;
    newType: string;
  }>;
  invalidConnections: string[]; // Connection IDs that would become invalid
}

/**
 * Get type information for a specific node
 */
export function getNodeTypeInfo(
  nodeId: string,
  modules: ModuleInstance[],
  templates: ModuleTemplate[]
): NodeTypeInfo | null {
  // Find the module and node
  for (const module of modules) {
    const allNodes = [...module.inputs, ...module.outputs];
    const node = allNodes.find(n => n.node_id === nodeId);

    if (node) {
      const template = templates.find(t => `${t.id}:${t.version}` === module.module_ref);
      if (!template) continue;

      const availableTypes = getAvailableTypesForNode(node, template);

      // Find the nodeSpec to get typeVar info
      const ioSide = node.direction === 'in'
        ? template.meta.io_shape.inputs
        : template.meta.io_shape.outputs;

      let typeVar: string | undefined;

      if ((node as any).is_static && ioSide.static) {
        const nodeSpec = ioSide.static.slots[(node as any).position_index];
        typeVar = nodeSpec?.typing.type_var;
      } else if (!(node as any).is_static && ioSide.dynamic && (node as any).group_key) {
        const group = ioSide.dynamic.groups.find(g => g.item.label === (node as any).group_key);
        typeVar = group?.item.typing.type_var;
      }

      return {
        nodeId,
        moduleId: module.module_instance_id,
        currentType: node.type,
        availableTypes,
        typeVar,
        isTypeVar: !!typeVar
      };
    }
  }

  return null;
}

/**
 * Get all nodes that share the same TypeVar within a module
 */
export function getTypeVarGroup(
  moduleId: string,
  typeVar: string,
  modules: ModuleInstance[]
): NodePin[] {
  const module = modules.find(m => m.module_instance_id === moduleId);
  if (!module) return [];

  const allNodes = [...module.inputs, ...module.outputs];

  return allNodes.filter(node => {
    // Check if this node uses the same typeVar
    // We need to check the node's type_var property
    return (node as any).type_var === typeVar;
  });
}

/**
 * Check if a connection between two nodes is valid
 */
export function validateConnection(
  fromNodeId: string,
  toNodeId: string,
  modules: ModuleInstance[],
  templates: ModuleTemplate[]
): ConnectionConstraint {
  const fromNode = getNodeTypeInfo(fromNodeId, modules, templates);
  const toNode = getNodeTypeInfo(toNodeId, modules, templates);

  if (!fromNode || !toNode) {
    return { isValid: false, reason: 'Node not found' };
  }

  // Check if types are compatible
  const compatibleTypes = fromNode.availableTypes.filter(type =>
    toNode.availableTypes.includes(type)
  );

  if (compatibleTypes.length === 0) {
    return {
      isValid: false,
      reason: `No compatible types between ${fromNode.availableTypes.join(', ')} and ${toNode.availableTypes.join(', ')}`
    };
  }

  // If both nodes have fixed types, check direct compatibility
  if (fromNode.availableTypes.length === 1 && toNode.availableTypes.length === 1) {
    const isCompatible = fromNode.currentType === toNode.currentType;
    return {
      isValid: isCompatible,
      requiredType: isCompatible ? fromNode.currentType : undefined,
      reason: isCompatible ? undefined : `Type mismatch: ${fromNode.currentType} vs ${toNode.currentType}`
    };
  }

  // If connection would force a type, return that type
  if (fromNode.availableTypes.length === 1) {
    return { isValid: true, requiredType: fromNode.currentType };
  }

  if (toNode.availableTypes.length === 1) {
    return { isValid: true, requiredType: toNode.currentType };
  }

  // Both are flexible, use first compatible type
  return { isValid: true, requiredType: compatibleTypes[0] };
}

/**
 * Calculate what type changes would be needed if a specific node type changes
 */
export function calculateTypePropagation(
  nodeId: string,
  newType: string,
  modules: ModuleInstance[],
  templates: ModuleTemplate[],
  connections: NodeConnection[]
): TypeChangePropagation {
  const result: TypeChangePropagation = {
    nodesToUpdate: [],
    invalidConnections: []
  };

  const nodeInfo = getNodeTypeInfo(nodeId, modules, templates);
  if (!nodeInfo) return result;

  // 1. If this is a TypeVar node, update all nodes in the same TypeVar group
  if (nodeInfo.isTypeVar && nodeInfo.typeVar) {
    const typeVarNodes = getTypeVarGroup(nodeInfo.moduleId, nodeInfo.typeVar, modules);

    for (const node of typeVarNodes) {
      if (node.node_id !== nodeId) {
        result.nodesToUpdate.push({
          moduleId: nodeInfo.moduleId,
          nodeId: node.node_id,
          newType
        });
      }
    }
  }

  // 2. Check connections and propagate to connected nodes
  const relatedConnections = connections.filter(conn =>
    conn.from_node_id === nodeId || conn.to_node_id === nodeId
  );

  for (const connection of relatedConnections) {
    const otherNodeId = connection.from_node_id === nodeId
      ? connection.to_node_id
      : connection.from_node_id;

    const otherNodeInfo = getNodeTypeInfo(otherNodeId, modules, templates);
    if (!otherNodeInfo) continue;

    // Check if the other node can accept the new type
    if (!otherNodeInfo.availableTypes.includes(newType)) {
      result.invalidConnections.push(`${connection.from_node_id}->${connection.to_node_id}`);
      continue;
    }

    // If the other node needs to change type
    if (otherNodeInfo.currentType !== newType) {
      result.nodesToUpdate.push({
        moduleId: otherNodeInfo.moduleId,
        nodeId: otherNodeInfo.nodeId,
        newType
      });

      // Recursively propagate from the other node
      const recursiveResult = calculateTypePropagation(
        otherNodeId,
        newType,
        modules,
        templates,
        connections
      );

      result.nodesToUpdate.push(...recursiveResult.nodesToUpdate);
      result.invalidConnections.push(...recursiveResult.invalidConnections);
    }
  }

  // Remove duplicates
  result.nodesToUpdate = result.nodesToUpdate.filter((item, index, arr) =>
    arr.findIndex(other => other.nodeId === item.nodeId) === index
  );

  result.invalidConnections = [...new Set(result.invalidConnections)];

  return result;
}

/**
 * Get restricted types for a TypeVar group based on connections
 */
export function getRestrictedTypesForTypeVar(
  moduleId: string,
  typeVar: string,
  modules: ModuleInstance[],
  templates: ModuleTemplate[],
  connections: NodeConnection[]
): string[] {
  const typeVarNodes = getTypeVarGroup(moduleId, typeVar, modules);
  if (typeVarNodes.length === 0) return [];

  // Get base available types for any node in the group
  const firstNode = typeVarNodes[0];
  const nodeInfo = getNodeTypeInfo(firstNode.node_id, modules, templates);
  if (!nodeInfo) return [];

  let restrictedTypes = [...nodeInfo.availableTypes];

  // Check each node in the TypeVar group for connection constraints
  for (const node of typeVarNodes) {
    const nodeConnections = connections.filter(conn =>
      conn.from_node_id === node.node_id || conn.to_node_id === node.node_id
    );

    for (const connection of nodeConnections) {
      const otherNodeId = connection.from_node_id === node.node_id
        ? connection.to_node_id
        : connection.from_node_id;

      const otherNodeInfo = getNodeTypeInfo(otherNodeId, modules, templates);
      if (!otherNodeInfo) continue;

      // Intersect with compatible types from connected node
      restrictedTypes = restrictedTypes.filter(type =>
        otherNodeInfo.availableTypes.includes(type)
      );
    }
  }

  return restrictedTypes;
}