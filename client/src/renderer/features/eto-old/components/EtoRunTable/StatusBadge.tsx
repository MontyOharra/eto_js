import { EtoRunStatus } from '../../types';

interface StatusBadgeProps {
  status: EtoRunStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const getStatusColor = (status: EtoRunStatus) => {
    switch (status) {
      case 'success':
        return 'text-green-400';
      case 'failure':
        return 'text-red-400';
      case 'needs_template':
        return 'text-yellow-400';
      case 'processing':
        return 'text-blue-400';
      case 'not_started':
        return 'text-gray-400';
      case 'skipped':
        return 'text-gray-500';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusLabel = (status: EtoRunStatus) => {
    switch (status) {
      case 'success':
        return 'Success';
      case 'failure':
        return 'Failed';
      case 'needs_template':
        return 'Needs Template';
      case 'processing':
        return 'Processing';
      case 'not_started':
        return 'Not Started';
      case 'skipped':
        return 'Skipped';
      default:
        return status;
    }
  };

  return (
    <span className={`text-xs font-medium ${getStatusColor(status)}`}>
      {getStatusLabel(status)}
    </span>
  );
}
