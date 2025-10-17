/**
 * Status Badge Component
 * Displays visual status indicators for email configurations
 */

interface StatusBadgeProps {
  type: 'active' | 'inactive' | 'running' | 'error';
  label?: string;
}

export function StatusBadge({ type, label }: StatusBadgeProps) {
  const config = {
    active: {
      text: label || 'Active',
      classes: 'bg-green-900/30 text-green-300 border-green-700',
    },
    inactive: {
      text: label || 'Inactive',
      classes: 'bg-gray-700/30 text-gray-300 border-gray-600',
    },
    running: {
      text: label || 'Running',
      classes: 'bg-blue-900/30 text-blue-300 border-blue-700',
    },
    error: {
      text: label || 'Error',
      classes: 'bg-red-900/30 text-red-300 border-red-700',
    },
  };

  const { text, classes } = config[type];

  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${classes}`}
    >
      {text}
    </span>
  );
}
