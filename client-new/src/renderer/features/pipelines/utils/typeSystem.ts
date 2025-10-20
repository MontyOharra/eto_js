/**
 * Type System Utilities
 * Pure functions for type constraint validation and propagation
 */

import { Node, Edge } from '@xyflow/react';
import { ModuleInstance, NodePin } from '../../../types/moduleTypes';

/**
 * Calculate intersection of two type arrays
 */
export function getTypeIntersection(types1: string[], types2: string[]): string[] {
  return types1.filter((type) => types2.includes(type));
}

/**
 * Get all pins from a module instance
 */
export function getAllPins(moduleInstance: ModuleInstance): NodePin[] {
  return [...moduleInstance.inputs, ...moduleInstance.outputs];
}

/**
 * Find a pin by ID within a module instance
 */
export function findPin(moduleInstance: ModuleInstance, pinId: string): NodePin | undefined {
  const allPins = getAllPins(moduleInstance);
  return allPins.find((p) => p.node_id === pinId);
}

/**
 * Get all pins with the same typevar within a module
 */
export function getPinsWithTypeVar(moduleInstance: ModuleInstance, typeVar: string): NodePin[] {
  const allPins = getAllPins(moduleInstance);
  return allPins.filter((p) => p.type_var === typeVar);
}

/**
 * Calculate effective allowed types for a pin based on entire connection graph.
 * Uses BFS to traverse all connected pins and typevar siblings.
 *
 * @param nodes - All nodes in the graph
 * @param edges - All edges in the graph
 * @param moduleId - Module containing the pin
 * @param pinId - Pin to calculate effective types for
 * @param baseAllowedTypes - Base allowed types from template
 * @returns Intersection of all type constraints in the connected graph
 */
export function getEffectiveAllowedTypes(
  nodes: Node[],
  edges: Edge[],
  moduleId: string,
  pinId: string,
  baseAllowedTypes: string[]
): string[] {
  const module = nodes.find((n) => n.id === moduleId);
  if (!module?.data?.moduleInstance) return baseAllowedTypes;

  const moduleInstance = module.data.moduleInstance as ModuleInstance;
  const currentPin = findPin(moduleInstance, pinId);
  if (!currentPin) return baseAllowedTypes;

  // Use BFS to traverse the entire connected graph and collect all type restrictions
  const visited = new Set<string>();
  const queue: Array<{ moduleId: string; pinId: string }> = [];
  let effectiveTypes = baseAllowedTypes;

  // Start with current pin
  queue.push({ moduleId, pinId });

  // If current pin has typevar, add all typevar siblings to start
  if (currentPin.type_var) {
    const typeVarPins = getPinsWithTypeVar(moduleInstance, currentPin.type_var);
    typeVarPins.forEach((pin) => {
      queue.push({ moduleId, pinId: pin.node_id });
    });
  }

  while (queue.length > 0) {
    const current = queue.shift()!;
    const key = `${current.moduleId}:${current.pinId}`;

    if (visited.has(key)) continue;
    visited.add(key);

    // Get the module and pin
    const mod = nodes.find((n) => n.id === current.moduleId);
    if (!mod?.data?.moduleInstance) continue;

    const modInstance = mod.data.moduleInstance as ModuleInstance;
    const pin = findPin(modInstance, current.pinId);
    if (!pin) continue;

    // Intersect with this pin's allowed types
    effectiveTypes = getTypeIntersection(effectiveTypes, pin.allowed_types || []);

    // If this pin has a typevar, add all typevar siblings
    if (pin.type_var) {
      const typeVarPins = getPinsWithTypeVar(modInstance, pin.type_var);
      typeVarPins.forEach((p) => {
        queue.push({ moduleId: current.moduleId, pinId: p.node_id });
      });
    }

    // Find all connected pins via edges
    edges.forEach((edge) => {
      if (edge.source === current.moduleId && edge.sourceHandle === current.pinId) {
        queue.push({ moduleId: edge.target!, pinId: edge.targetHandle! });
      } else if (edge.target === current.moduleId && edge.targetHandle === current.pinId) {
        queue.push({ moduleId: edge.source!, pinId: edge.sourceHandle! });
      }
    });
  }

  return effectiveTypes;
}

/**
 * Validate if two pins can be connected based on type constraints.
 * Uses effective allowed types which account for existing connections and typevars.
 *
 * @param nodes - All nodes in the graph
 * @param edges - All edges in the graph
 * @param sourceModuleId - ID of source module
 * @param sourcePin - Source pin to connect from
 * @param targetModuleId - ID of target module
 * @param targetPin - Target pin to connect to
 * @returns Object with validation result and suggested type if valid
 */
export function validateConnection(
  nodes: Node[],
  edges: Edge[],
  sourceModuleId: string,
  sourcePin: NodePin,
  targetModuleId: string,
  targetPin: NodePin
): {
  valid: boolean;
  suggestedType?: string;
  typeIntersection?: string[];
} {
  // Calculate effective allowed types for both pins based on graph context
  const sourceEffectiveTypes = getEffectiveAllowedTypes(
    nodes,
    edges,
    sourceModuleId,
    sourcePin.node_id,
    sourcePin.allowed_types || ['str']
  );

  const targetEffectiveTypes = getEffectiveAllowedTypes(
    nodes,
    edges,
    targetModuleId,
    targetPin.node_id,
    targetPin.allowed_types || ['str']
  );

  // Find intersection of effective types
  const typeIntersection = getTypeIntersection(sourceEffectiveTypes, targetEffectiveTypes);

  if (typeIntersection.length === 0) {
    return { valid: false };
  }

  // Determine which type to use
  let suggestedType: string;
  const sourceTypeInIntersection = typeIntersection.includes(sourcePin.type);
  const targetTypeInIntersection = typeIntersection.includes(targetPin.type);

  if (sourceTypeInIntersection) {
    // Source pin's type is in intersection - use it
    suggestedType = sourcePin.type;
  } else if (targetTypeInIntersection) {
    // Target pin's type is in intersection - use it
    suggestedType = targetPin.type;
  } else {
    // Neither type in intersection, use first shared type
    suggestedType = typeIntersection[0];
  }

  return {
    valid: true,
    suggestedType,
    typeIntersection,
  };
}

/**
 * Type propagation update to apply to a module
 */
export interface TypeUpdate {
  moduleId: string;
  pinId: string;
  newType: string;
}

/**
 * Calculate all type updates that need to cascade through the graph.
 * Uses BFS to propagate type changes through connections and typevars.
 *
 * @param nodes - All nodes in graph
 * @param edges - All edges in graph
 * @param initialUpdates - Initial type changes to propagate
 * @returns Array of all updates to apply
 */
export function calculateTypePropagation(
  nodes: Node[],
  edges: Edge[],
  initialUpdates: TypeUpdate[]
): TypeUpdate[] {
  const allUpdates: TypeUpdate[] = [];
  const queue: TypeUpdate[] = [...initialUpdates];
  const processed = new Set<string>();

  while (queue.length > 0) {
    const update = queue.shift()!;
    const key = `${update.moduleId}:${update.pinId}`;

    if (processed.has(key)) continue;
    processed.add(key);

    const moduleNode = nodes.find((n) => n.id === update.moduleId);
    if (!moduleNode?.data?.moduleInstance) continue;

    const moduleInstance = moduleNode.data.moduleInstance as ModuleInstance;
    const targetPin = findPin(moduleInstance, update.pinId);
    if (!targetPin) continue;

    // Skip if type is already correct
    if (targetPin.type === update.newType) {
      // Still need to propagate to connections
      edges.forEach((edge) => {
        if (edge.source === update.moduleId && edge.sourceHandle === update.pinId) {
          queue.push({
            moduleId: edge.target!,
            pinId: edge.targetHandle!,
            newType: update.newType,
          });
        } else if (edge.target === update.moduleId && edge.targetHandle === update.pinId) {
          queue.push({
            moduleId: edge.source!,
            pinId: edge.sourceHandle!,
            newType: update.newType,
          });
        }
      });
      continue;
    }

    // Check if new type is allowed
    const allowedTypes = targetPin.allowed_types || [];
    if (allowedTypes.length > 0 && !allowedTypes.includes(update.newType)) {
      continue; // Type not allowed, skip
    }

    // Record this update
    allUpdates.push(update);

    // If pin has typevar, add all typevar siblings to queue
    if (targetPin.type_var) {
      const typeVarPins = getPinsWithTypeVar(moduleInstance, targetPin.type_var);
      typeVarPins.forEach((pin) => {
        if (pin.node_id !== update.pinId) {
          queue.push({
            moduleId: update.moduleId,
            pinId: pin.node_id,
            newType: update.newType,
          });
        }
      });
    }

    // Add all connected pins to queue
    edges.forEach((edge) => {
      if (edge.source === update.moduleId && edge.sourceHandle === update.pinId) {
        queue.push({
          moduleId: edge.target!,
          pinId: edge.targetHandle!,
          newType: update.newType,
        });
      } else if (edge.target === update.moduleId && edge.targetHandle === update.pinId) {
        queue.push({
          moduleId: edge.source!,
          pinId: edge.sourceHandle!,
          newType: update.newType,
        });
      }
    });
  }

  return allUpdates;
}

/**
 * Apply type updates to nodes array immutably
 */
export function applyTypeUpdates(nodes: Node[], updates: TypeUpdate[]): Node[] {
  // Group updates by module
  const updatesByModule = new Map<string, Map<string, string>>();

  updates.forEach((update) => {
    if (!updatesByModule.has(update.moduleId)) {
      updatesByModule.set(update.moduleId, new Map());
    }
    updatesByModule.get(update.moduleId)!.set(update.pinId, update.newType);
  });

  // Apply updates
  return nodes.map((node) => {
    const moduleUpdates = updatesByModule.get(node.id);
    if (!moduleUpdates || !node.data?.moduleInstance) return node;

    const moduleInstance = node.data.moduleInstance as ModuleInstance;

    const updatedInputs = moduleInstance.inputs.map((input) => {
      const newType = moduleUpdates.get(input.node_id);
      return newType ? { ...input, type: newType } : input;
    });

    const updatedOutputs = moduleInstance.outputs.map((output) => {
      const newType = moduleUpdates.get(output.node_id);
      return newType ? { ...output, type: newType } : output;
    });

    return {
      ...node,
      data: {
        ...node.data,
        moduleInstance: {
          ...moduleInstance,
          inputs: updatedInputs,
          outputs: updatedOutputs,
        },
      },
    };
  });
}
