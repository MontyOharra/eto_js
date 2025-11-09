/**
 * Type System Utilities
 * Pure functions for type constraint validation and propagation
 */

import { PipelineState, EntryPoint, ModuleInstance, NodePin } from "../types";

/**
 * Calculate intersection of two type arrays
 */
export function getTypeIntersection(
  types1: string[],
  types2: string[]
): string[] {
  return types1.filter((type) => types2.includes(type));
}

/**
 * Get all pins from a module instance (internal helper)
 */
function getAllPins(moduleInstance: ModuleInstance): NodePin[] {
  return [...moduleInstance.inputs, ...moduleInstance.outputs];
}

/**
 * Find a pin by ID within a module instance
 */
export function findPinInModule(
  moduleInstance: ModuleInstance,
  pinId: string
): NodePin | undefined {
  const allPins = getAllPins(moduleInstance);
  return allPins.find((p) => p.node_id === pinId);
}

/**
 * Find a module by ID in pipeline state
 */
function findModule(
  pipelineState: PipelineState,
  effectiveEntryPoints: EntryPoint[],
  moduleId: string
): { module: ModuleInstance; isEntryPoint: boolean } | undefined {
  // Check if it's an entry point
  const entryPoint = effectiveEntryPoints.find((ep) => ep.entry_point_id === moduleId);
  if (entryPoint) {
    // Convert EntryPoint to ModuleInstance structure
    const moduleInstance: ModuleInstance = {
      module_instance_id: entryPoint.entry_point_id,
      module_ref: "entry_point:1.0.0",
      config: {},
      inputs: [],
      outputs: entryPoint.outputs,
    };
    return { module: moduleInstance, isEntryPoint: true };
  }

  // Check regular modules
  const module = pipelineState.modules.find((m) => m.module_instance_id === moduleId);
  if (module) {
    return { module, isEntryPoint: false };
  }

  return undefined;
}

/**
 * Get all pins with the same typevar within a module
 */
export function getPinsWithTypeVar(
  moduleInstance: ModuleInstance,
  typeVar: string
): NodePin[] {
  const allPins = getAllPins(moduleInstance);
  return allPins.filter((p) => p.type_var === typeVar);
}

/**
 * Calculate effective allowed types for a pin based on entire connection graph.
 * Uses BFS to traverse all connected pins and typevar siblings.
 *
 * @param pipelineState - Pipeline state containing modules and connections
 * @param effectiveEntryPoints - Entry points in the pipeline
 * @param moduleId - Module containing the pin
 * @param pinId - Pin to calculate effective types for
 * @param baseAllowedTypes - Base allowed types from template
 * @returns Intersection of all type constraints in the connected graph
 */
export function getEffectiveAllowedTypes(
  pipelineState: PipelineState,
  effectiveEntryPoints: EntryPoint[],
  moduleId: string,
  pinId: string,
  baseAllowedTypes: string[]
): string[] {
  const moduleData = findModule(pipelineState, effectiveEntryPoints, moduleId);
  if (!moduleData) return baseAllowedTypes;

  const currentPin = findPinInModule(moduleData.module, pinId);
  if (!currentPin) return baseAllowedTypes;

  // Use BFS to traverse the entire connected graph and collect all type restrictions
  const visited = new Set<string>();
  const queue: Array<{ moduleId: string; pinId: string }> = [];
  let effectiveTypes = baseAllowedTypes;

  // Start with current pin
  queue.push({ moduleId, pinId });

  // If current pin has typevar, add all typevar siblings to start
  if (currentPin.type_var) {
    const typeVarPins = getPinsWithTypeVar(moduleData.module, currentPin.type_var);
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
    const modData = findModule(pipelineState, effectiveEntryPoints, current.moduleId);
    if (!modData) continue;

    const pin = findPinInModule(modData.module, current.pinId);
    if (!pin) continue;

    // Intersect with this pin's allowed types
    effectiveTypes = getTypeIntersection(
      effectiveTypes,
      pin.allowed_types || []
    );

    // If this pin has a typevar, add all typevar siblings
    if (pin.type_var) {
      const typeVarPins = getPinsWithTypeVar(modData.module, pin.type_var);
      typeVarPins.forEach((p) => {
        queue.push({ moduleId: current.moduleId, pinId: p.node_id });
      });
    }

    // Find all connected pins via connections
    pipelineState.connections.forEach((conn) => {
      if (conn.from_node_id === current.pinId) {
        // Find which module owns the target pin
        const targetModuleId = findModuleIdForPin(pipelineState, effectiveEntryPoints, conn.to_node_id);
        if (targetModuleId) {
          queue.push({ moduleId: targetModuleId, pinId: conn.to_node_id });
        }
      } else if (conn.to_node_id === current.pinId) {
        // Find which module owns the source pin
        const sourceModuleId = findModuleIdForPin(pipelineState, effectiveEntryPoints, conn.from_node_id);
        if (sourceModuleId) {
          queue.push({ moduleId: sourceModuleId, pinId: conn.from_node_id });
        }
      }
    });
  }

  return effectiveTypes;
}

/**
 * Find which module owns a given pin (internal helper)
 */
function findModuleIdForPin(
  pipelineState: PipelineState,
  effectiveEntryPoints: EntryPoint[],
  pinId: string
): string | undefined {
  // Check entry points
  for (const ep of effectiveEntryPoints) {
    if (ep.outputs.some((p) => p.node_id === pinId)) {
      return ep.entry_point_id;
    }
  }

  // Check modules
  for (const module of pipelineState.modules) {
    const allPins = [...module.inputs, ...module.outputs];
    if (allPins.some((p) => p.node_id === pinId)) {
      return module.module_instance_id;
    }
  }

  return undefined;
}

/**
 * Validate if two pins can be connected based on type constraints.
 * Uses effective allowed types which account for existing connections and typevars.
 *
 * @param pipelineState - Pipeline state containing modules and connections
 * @param effectiveEntryPoints - Entry points in the pipeline
 * @param sourceModuleId - ID of source module
 * @param sourcePinId - ID of source pin to connect from
 * @param targetModuleId - ID of target module
 * @param targetPinId - ID of target pin to connect to
 * @returns Object with validation result and suggested type if valid
 */
export function validateConnection(
  pipelineState: PipelineState,
  effectiveEntryPoints: EntryPoint[],
  sourceModuleId: string,
  sourcePinId: string,
  targetModuleId: string,
  targetPinId: string
): {
  valid: boolean;
  suggestedType?: string;
  typeIntersection?: string[];
} {
  // Find source and target pins
  const sourceModuleData = findModule(pipelineState, effectiveEntryPoints, sourceModuleId);
  const targetModuleData = findModule(pipelineState, effectiveEntryPoints, targetModuleId);

  if (!sourceModuleData || !targetModuleData) {
    return { valid: false };
  }

  const sourcePin = findPinInModule(sourceModuleData.module, sourcePinId);
  const targetPin = findPinInModule(targetModuleData.module, targetPinId);

  if (!sourcePin || !targetPin) {
    return { valid: false };
  }

  // Calculate effective allowed types for both pins based on graph context
  const sourceEffectiveTypes = getEffectiveAllowedTypes(
    pipelineState,
    effectiveEntryPoints,
    sourceModuleId,
    sourcePinId,
    sourcePin.allowed_types || ["str"]
  );

  const targetEffectiveTypes = getEffectiveAllowedTypes(
    pipelineState,
    effectiveEntryPoints,
    targetModuleId,
    targetPinId,
    targetPin.allowed_types || ["str"]
  );

  // Find intersection of effective types
  const typeIntersection = getTypeIntersection(
    sourceEffectiveTypes,
    targetEffectiveTypes
  );

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
 * @param pipelineState - Pipeline state containing modules and connections
 * @param effectiveEntryPoints - Entry points in the pipeline
 * @param initialUpdates - Initial type changes to propagate
 * @returns Array of all updates to apply
 */
export function calculateTypePropagation(
  pipelineState: PipelineState,
  effectiveEntryPoints: EntryPoint[],
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

    const moduleData = findModule(pipelineState, effectiveEntryPoints, update.moduleId);
    if (!moduleData) continue;

    const targetPin = findPinInModule(moduleData.module, update.pinId);
    if (!targetPin) continue;

    // Skip entry point pins - they are always 'str' and readonly
    if (moduleData.isEntryPoint) {
      continue;
    }

    // Skip if type is already correct
    if (targetPin.type === update.newType) {
      // Still need to propagate to connections
      pipelineState.connections.forEach((conn) => {
        if (conn.from_node_id === update.pinId) {
          const targetModuleId = findModuleIdForPin(pipelineState, effectiveEntryPoints, conn.to_node_id);
          if (targetModuleId) {
            queue.push({
              moduleId: targetModuleId,
              pinId: conn.to_node_id,
              newType: update.newType,
            });
          }
        } else if (conn.to_node_id === update.pinId) {
          const sourceModuleId = findModuleIdForPin(pipelineState, effectiveEntryPoints, conn.from_node_id);
          if (sourceModuleId) {
            queue.push({
              moduleId: sourceModuleId,
              pinId: conn.from_node_id,
              newType: update.newType,
            });
          }
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
      const typeVarPins = getPinsWithTypeVar(
        moduleData.module,
        targetPin.type_var
      );
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
    pipelineState.connections.forEach((conn) => {
      if (conn.from_node_id === update.pinId) {
        const targetModuleId = findModuleIdForPin(pipelineState, effectiveEntryPoints, conn.to_node_id);
        if (targetModuleId) {
          queue.push({
            moduleId: targetModuleId,
            pinId: conn.to_node_id,
            newType: update.newType,
          });
        }
      } else if (conn.to_node_id === update.pinId) {
        const sourceModuleId = findModuleIdForPin(pipelineState, effectiveEntryPoints, conn.from_node_id);
        if (sourceModuleId) {
          queue.push({
            moduleId: sourceModuleId,
            pinId: conn.from_node_id,
            newType: update.newType,
          });
        }
      }
    });
  }

  return allUpdates;
}

/**
 * Apply type updates to pipeline state immutably
 * Returns updated PipelineState with all type changes applied
 */
export function applyTypeUpdates(
  pipelineState: PipelineState,
  updates: TypeUpdate[]
): PipelineState {
  // Group updates by module
  const updatesByModule = new Map<string, Map<string, string>>();

  updates.forEach((update) => {
    if (!updatesByModule.has(update.moduleId)) {
      updatesByModule.set(update.moduleId, new Map());
    }
    updatesByModule.get(update.moduleId)!.set(update.pinId, update.newType);
  });

  // Apply updates to modules (skip entry points - they're always 'str')
  const updatedModules = pipelineState.modules.map((module) => {
    const moduleUpdates = updatesByModule.get(module.module_instance_id);
    if (!moduleUpdates) return module;

    const updatedInputs = module.inputs.map((input) => {
      const newType = moduleUpdates.get(input.node_id);
      return newType ? { ...input, type: newType } : input;
    });

    const updatedOutputs = module.outputs.map((output) => {
      const newType = moduleUpdates.get(output.node_id);
      return newType ? { ...output, type: newType } : output;
    });

    return {
      ...module,
      inputs: updatedInputs,
      outputs: updatedOutputs,
    };
  });

  return {
    ...pipelineState,
    modules: updatedModules,
  };
}
