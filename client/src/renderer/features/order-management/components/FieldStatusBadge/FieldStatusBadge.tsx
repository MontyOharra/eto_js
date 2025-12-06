/**
 * FieldStatusBadge Component
 *
 * Displays field completion status for pending orders.
 * Shows count of present/missing fields with visual indicator.
 */

import type { PendingOrderFieldStatus } from '../../types';

interface FieldStatusBadgeProps {
  fieldStatus: PendingOrderFieldStatus;
  /** Show detailed breakdown or just summary */
  detailed?: boolean;
  className?: string;
}

export function FieldStatusBadge({
  fieldStatus,
  detailed = false,
  className = '',
}: FieldStatusBadgeProps) {
  const presentCount = fieldStatus.present.length;
  const missingRequiredCount = fieldStatus.missing_required.length;
  const totalRequired = presentCount + missingRequiredCount;

  const isComplete = missingRequiredCount === 0;

  if (detailed) {
    return (
      <div className={`flex flex-col gap-1 ${className}`}>
        {/* Present fields */}
        {fieldStatus.present.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {fieldStatus.present.map((field) => (
              <span
                key={field}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400 border border-green-500/30"
              >
                {formatFieldName(field)}
              </span>
            ))}
          </div>
        )}

        {/* Missing required fields */}
        {fieldStatus.missing_required.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {fieldStatus.missing_required.map((field) => (
              <span
                key={field}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400 border border-red-500/30"
              >
                {formatFieldName(field)}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Summary view
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        isComplete
          ? 'bg-green-500/20 text-green-400 border-green-500/30'
          : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
      } ${className}`}
    >
      <span className="font-semibold">{presentCount}</span>
      <span className="text-gray-400">/</span>
      <span>{totalRequired}</span>
      <span className="text-gray-400">fields</span>
    </span>
  );
}

/**
 * Convert field_name to Field Name
 */
function formatFieldName(fieldName: string): string {
  return fieldName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
