/**
 * Edge Utilities
 * Functions for type-based edge coloring
 */

import { TYPE_COLORS } from "./moduleUtils";

/**
 * Get color for a type
 */
export function getTypeColor(type: string): string {
  return TYPE_COLORS[type] || "#6B7280"; // gray-500 fallback
}
