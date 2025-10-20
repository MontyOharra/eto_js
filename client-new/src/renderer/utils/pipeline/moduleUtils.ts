/**
 * Module utility functions and constants
 */

import { NodePin } from '../../types/moduleTypes';

/**
 * Type to color mapping for visual representation
 */
export const TYPE_COLORS: Record<string, string> = {
  str: '#3B82F6', // blue-500
  int: '#F59E0B', // orange-500
  float: '#F59E0B', // orange-500
  bool: '#10B981', // green-500
  datetime: '#8B5CF6', // purple-500
};

/**
 * Calculate if text should be white or black based on background brightness
 * Uses perceived brightness formula
 */
export function getTextColor(hexColor: string): string {
  const hex = hexColor.replace('#', '');
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  return brightness > 128 ? '#000000' : '#FFFFFF';
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
