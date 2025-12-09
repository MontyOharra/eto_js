/**
 * FieldStatusBadge Component
 *
 * Displays field completion status for pending orders.
 * Shows count of present/missing fields with visual indicator.
 */

interface FieldStatusBadgeProps {
  /** Number of required fields present */
  requiredPresent: number;
  /** Total number of required fields */
  requiredTotal: number;
  /** Number of fields with conflicts */
  conflictCount: number;
  className?: string;
}

export function FieldStatusBadge({
  requiredPresent,
  requiredTotal,
  conflictCount,
  className = '',
}: FieldStatusBadgeProps) {
  const isComplete = requiredPresent >= requiredTotal;
  const hasConflicts = conflictCount > 0;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Field count badge */}
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
          isComplete
            ? 'bg-green-500/20 text-green-400 border-green-500/30'
            : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
        }`}
      >
        <span className="font-semibold">{requiredPresent}</span>
        <span className="text-gray-400">/</span>
        <span>{requiredTotal}</span>
        <span className="text-gray-400">fields</span>
      </span>

      {/* Conflict indicator */}
      {hasConflicts && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span>{conflictCount}</span>
        </span>
      )}
    </div>
  );
}
