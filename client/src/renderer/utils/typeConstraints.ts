/**
 * Type constraint system for TypeVar coordination and connection validation
 */

import { ModuleInstance, ModuleTemplate, NodePin } from '../types/moduleTypes';
import { NodeConnection } from '../types/pipelineTypes';
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
 * Find all nodes that are connected to a given node through the entire constraint network
 * This includes direct connections AND TypeVar relationships
 */
export function getConstraintNetwork(
  startNodeId: string,
  modules: ModuleInstance[],
  templates: ModuleTemplate[],
  connections: NodeConnection[]
): Set<string> {
  const networkNodes = new Set<string>();
  const toVisit = [startNodeId];

  while (toVisit.length > 0) {
    const currentNodeId = toVisit.shift()!;

    if (networkNodes.has(currentNodeId)) {
      continue; // Already processed this node
    }

    networkNodes.add(currentNodeId);

    // Find all nodes connected to this one
    const connectedNodes = getDirectlyConnectedNodes(currentNodeId, modules, templates, connections);

    for (const connectedNodeId of connectedNodes) {
      if (!networkNodes.has(connectedNodeId)) {
        toVisit.push(connectedNodeId);
      }
    }
  }

  return networkNodes;
}

/**
 * Get all nodes directly connected to a given node (via connections OR TypeVars)
 */
function getDirectlyConnectedNodes(
  nodeId: string,
  modules: ModuleInstance[],
  templates: ModuleTemplate[],
  connections: NodeConnection[]
): string[] {
  const connectedNodes: string[] = [];

  // 1. Find nodes connected via actual connections
  const directConnections = connections.filter(conn =>
    conn.from_node_id === nodeId || conn.to_node_id === nodeId
  );

  for (const connection of directConnections) {
    const otherNodeId = connection.from_node_id === nodeId
      ? connection.to_node_id
      : connection.from_node_id;
    connectedNodes.push(otherNodeId);
  }

  // 2. Find nodes connected via TypeVar relationships
  const nodeInfo = getNodeTypeInfo(nodeId, modules, templates);
  if (nodeInfo && nodeInfo.isTypeVar && nodeInfo.typeVar) {
    const typeVarNodes = getTypeVarGroup(nodeInfo.moduleId, nodeInfo.typeVar, modules);

    for (const typeVarNode of typeVarNodes) {
      if (typeVarNode.node_id !== nodeId) {
        connectedNodes.push(typeVarNode.node_id);
      }
    }
  }

  return connectedNodes;
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
 * Now considers the entire constraint network
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

  // Find the entire constraint network for this node
  const constraintNetwork = getConstraintNetwork(nodeId, modules, templates, connections);

  // Check if the new type is valid for the entire network
  for (const networkNodeId of constraintNetwork) {
    const networkNodeInfo = getNodeTypeInfo(networkNodeId, modules, templates);
    if (!networkNodeInfo) continue;

    // If any node in the network can't support the new type, find invalid connections
    if (!networkNodeInfo.availableTypes.includes(newType)) {
      // Find connections that would become invalid
      const nodeConnections = connections.filter(conn =>
        (conn.from_node_id === networkNodeId || conn.to_node_id === networkNodeId) &&
        (constraintNetwork.has(conn.from_node_id) && constraintNetwork.has(conn.to_node_id))
      );

      for (const connection of nodeConnections) {
        result.invalidConnections.push(`${connection.from_node_id}->${connection.to_node_id}`);
      }
    }
  }

  // If there are invalid connections, don't proceed with updates
  if (result.invalidConnections.length > 0) {
    return result;
  }

  // Update all nodes in the constraint network that need to change
  for (const networkNodeId of constraintNetwork) {
    if (networkNodeId === nodeId) continue; // Skip the original node

    const networkNodeInfo = getNodeTypeInfo(networkNodeId, modules, templates);
    if (!networkNodeInfo) continue;

    // Only update if the node's current type is different from the new type
    if (networkNodeInfo.currentType !== newType) {
      result.nodesToUpdate.push({
        moduleId: networkNodeInfo.moduleId,
        nodeId: networkNodeId,
        newType
      });
    }
  }

  // Remove duplicates
  result.nodesToUpdate = result.nodesToUpdate.filter((item, index, arr) =>
    arr.findIndex(other => other.nodeId === item.nodeId) === index
  );

  result.invalidConnections = Array.from(new Set(result.invalidConnections));

  return result;
}

/**
 * Get allowed and disabled types for a node based on network-wide constraints
 */
export function getNodeTypeConstraints(
  nodeId: string,
  modules: ModuleInstance[],
  templates: ModuleTemplate[],
  connections: NodeConnection[]
): { allowedTypes: string[]; disabledTypes: string[]; allTypes: string[] } {
  const ALL_TYPES = ['str', 'int', 'float', 'bool', 'datetime'];

  const nodeInfo = getNodeTypeInfo(nodeId, modules, templates);
  if (!nodeInfo) {
    return { allowedTypes: ALL_TYPES, disabledTypes: [], allTypes: ALL_TYPES };
  }

  // Find the entire constraint network for this node
  const constraintNetwork = getConstraintNetwork(nodeId, modules, templates, connections);

  // If the network only contains this node (no connections or TypeVars), return base types
  if (constraintNetwork.size === 1) {
    return {
      allowedTypes: [...nodeInfo.availableTypes],
      disabledTypes: ALL_TYPES.filter(type => !nodeInfo.availableTypes.includes(type)),
      allTypes: ALL_TYPES
    };
  }

  // Calculate the intersection of allowed types across the entire network
  let networkAllowedTypes = [...ALL_TYPES]; // Start with all possible types

  for (const networkNodeId of constraintNetwork) {
    const networkNodeInfo = getNodeTypeInfo(networkNodeId, modules, templates);
    if (!networkNodeInfo) continue;

    // Intersect with this node's available types
    networkAllowedTypes = networkAllowedTypes.filter(type =>
      networkNodeInfo.availableTypes.includes(type)
    );
  }

  // The allowed types for this specific node are the intersection of:
  // 1. The node's base available types
  // 2. The network-wide allowed types
  const allowedTypes = nodeInfo.availableTypes.filter(type =>
    networkAllowedTypes.includes(type)
  );

  // Determine disabled types
  const disabledTypes = ALL_TYPES.filter(type => !allowedTypes.includes(type));

  return {
    allowedTypes,
    disabledTypes,
    allTypes: ALL_TYPES
  };
}

/**
 * Connection creation result
 */
export interface ConnectionCreationResult {
  canConnect: boolean;
  reason?: string;
  typeChanges?: Array<{
    moduleId: string;
    nodeId: string;
    newType: string;
  }>;
}

/**
 * Validates if two nodes can be connected and determines type changes needed
 * Now considers network-wide constraints for both TypeVar and non-TypeVar nodes
 */
export function validateAndPrepareConnection(
  fromNodeId: string,
  toNodeId: string,
  modules: ModuleInstance[],
  templates: ModuleTemplate[],
  connections: NodeConnection[]
): ConnectionCreationResult {
  const fromNodeInfo = getNodeTypeInfo(fromNodeId, modules, templates);
  const toNodeInfo = getNodeTypeInfo(toNodeId, modules, templates);

  if (!fromNodeInfo || !toNodeInfo) {
    return { canConnect: false, reason: 'Node not found' };
  }

  // Find the constraint networks for both nodes
  const fromNetwork = getConstraintNetwork(fromNodeId, modules, templates, connections);
  const toNetwork = getConstraintNetwork(toNodeId, modules, templates, connections);

  // Calculate the constraint intersection for the combined network
  const combinedNetwork = new Set([...fromNetwork, ...toNetwork]);
  let networkAllowedTypes = ['str', 'int', 'float', 'bool', 'datetime'];

  for (const networkNodeId of combinedNetwork) {
    const networkNodeInfo = getNodeTypeInfo(networkNodeId, modules, templates);
    if (!networkNodeInfo) continue;

    // Intersect with this node's available types
    networkAllowedTypes = networkAllowedTypes.filter(type =>
      networkNodeInfo.availableTypes.includes(type)
    );
  }

  // If no types are compatible across the entire network, connection is not allowed
  if (networkAllowedTypes.length === 0) {
    return {
      canConnect: false,
      reason: 'No compatible types across the constraint network'
    };
  }

  // Determine the target type for the connection
  let targetType: string;

  // Priority logic:
  // 1. If from node's current type is in allowed types, use it
  // 2. If to node's current type is in allowed types, use it
  // 3. Use first allowed type
  if (networkAllowedTypes.includes(fromNodeInfo.currentType)) {
    targetType = fromNodeInfo.currentType;
  } else if (networkAllowedTypes.includes(toNodeInfo.currentType)) {
    targetType = toNodeInfo.currentType;
  } else {
    targetType = networkAllowedTypes[0];
  }

  // Calculate all type changes needed for the entire combined network
  const typeChanges: Array<{ moduleId: string; nodeId: string; newType: string }> = [];

  for (const networkNodeId of combinedNetwork) {
    const networkNodeInfo = getNodeTypeInfo(networkNodeId, modules, templates);
    if (!networkNodeInfo) continue;

    // Only add type change if the current type is different
    if (networkNodeInfo.currentType !== targetType) {
      typeChanges.push({
        moduleId: networkNodeInfo.moduleId,
        nodeId: networkNodeId,
        newType: targetType
      });
    }
  }

  return { canConnect: true, typeChanges };
}