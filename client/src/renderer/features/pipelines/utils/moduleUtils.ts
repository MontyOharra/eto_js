/**
 * Module utility functions and constants
 */

import { NodePin, EntryPoint, ModuleInstance, OutputChannelInstance } from "../types";
import { updatePinInModule } from "./moduleFactory";

/**
 * Type to color mapping for visual representation
 */
export const TYPE_COLORS: Record<string, string> = {
  str: "#3B82F6", // blue-500
  int: "#DC2626", // red-600 (dark red)
  float: "#FCA5A5", // red-300 (light red)
  bool: "#10B981", // green-500
  datetime: "#8B5CF6", // purple-500
  "list[str]": "#F59E0B", // amber-500
};

/**
 * Calculate if text should be white or black based on background brightness
 * Uses perceived brightness formula
 */
export function getTextColor(hexColor: string): string {
  const hex = hexColor.replace("#", "");
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  return brightness > 128 ? "#000000" : "#FFFFFF";
}

/**
 * Group nodes by their group_index for rendering
 * Returns a Map of group index to array of nodes in that group
 */
export function groupNodesByIndex(nodes: NodePin[]): Map<number, NodePin[]> {
  const groups = new Map<number, NodePin[]>();

  nodes.forEach((node) => {
    const groupIndex = node.group_index;
    if (!groups.has(groupIndex)) {
      groups.set(groupIndex, []);
    }
    groups.get(groupIndex)!.push(node);
  });

  return groups;
}

/**
 * Find a pin by its node_id across entry points, modules, and output channels
 * Useful for searching through the entire pipeline state
 */
export function findPinInPipeline(
  nodeId: string,
  entryPoints: EntryPoint[],
  modules: ModuleInstance[],
  outputChannels: OutputChannelInstance[] = []
): NodePin | undefined {
  // Check entry points
  for (const ep of entryPoints) {
    const pin = ep.outputs.find((p) => p.node_id === nodeId);
    if (pin) return pin;
  }

  // Check modules
  for (const module of modules) {
    const pin = [...module.inputs, ...module.outputs].find((p) => p.node_id === nodeId);
    if (pin) return pin;
  }

  // Check output channels
  for (const oc of outputChannels) {
    const pin = oc.inputs.find((p) => p.node_id === nodeId);
    if (pin) return pin;
  }

  return undefined;
}

/**
 * Synchronize type changes across all pins with the same type_var
 * Returns updated module with all linked pins changed to the new type
 */
export function synchronizeTypeVarUpdate(
  module: ModuleInstance,
  nodeId: string,
  newType: string
): { updatedModule: ModuleInstance; wasTypeVarUpdate: boolean } {
  const allPins = [...module.inputs, ...module.outputs];
  const targetPin = allPins.find((p) => p.node_id === nodeId);

  // If pin has type_var, update all pins with same type_var
  if (targetPin?.type_var) {
    let updatedModule = module;
    allPins.forEach((pin) => {
      if (pin.type_var === targetPin.type_var) {
        updatedModule = updatePinInModule(updatedModule, pin.node_id, { type: newType });
      }
    });

    return { updatedModule, wasTypeVarUpdate: true };
  }

  // No type_var, just update the single pin
  return { updatedModule: updatePinInModule(module, nodeId, { type: newType }), wasTypeVarUpdate: false };
}

/**
 * Check if two pins can connect based on shared allowed types
 * Returns true if the pins share at least one common type
 */
export function pinsCanConnect(sourcePin: NodePin, targetPin: NodePin): boolean {
  // Ensure source is output and target is input
  if (sourcePin.direction !== 'out' || targetPin.direction !== 'in') {
    return false;
  }

  const sourceAllowedTypes = sourcePin.allowed_types || [];
  const targetAllowedTypes = targetPin.allowed_types || [];

  // Check if there's at least one shared type
  const sharedTypes = sourceAllowedTypes.filter(type =>
    targetAllowedTypes.includes(type)
  );

  return sharedTypes.length > 0;
}
