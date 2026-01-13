/**
 * Shared constants for Order Management feature
 */

/**
 * Status color styling for pending action statuses.
 * Used consistently across list view and detail views.
 *
 * Format: Tailwind classes for background, text, and border colors
 */
export const STATUS_COLORS: Record<string, string> = {
  incomplete: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  conflict: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  ambiguous: 'bg-red-500/20 text-red-400 border-red-500/30',
  ready: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  processing: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  completed: 'bg-green-500/20 text-green-400 border-green-500/30',
  failed: 'bg-red-500/20 text-red-400 border-red-500/30',
  rejected: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  // Aliases for backward compatibility
  created: 'bg-green-500/20 text-green-400 border-green-500/30',
  pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  approved: 'bg-green-500/20 text-green-400 border-green-500/30',
};

/**
 * Get status color classes, with fallback for unknown statuses
 */
export function getStatusColorClasses(status: string): string {
  return STATUS_COLORS[status] ?? 'bg-gray-500/20 text-gray-400 border-gray-500/30';
}
