import { EtoSubRunStatus } from '../../types';

interface StatusBadgeProps {
  status: EtoSubRunStatus;
}

export function EtoSubRunStatusBadge({ status }: StatusBadgeProps) {
  const getStatusColor = (status: EtoSubRunStatus) => {
    switch (status) {
      case 'success':
        return 'text-green-400';
      case 'failure':
        return 'text-red-400';
      case 'processing':
        return 'text-blue-400';
      case 'skipped':
        return 'text-gray-500';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusLabel = (status: EtoSubRunStatus) => {
    switch (status) {
      case 'success':
        return 'Success';
      case 'failure':
        return 'Failed';
      case 'processing':
        return 'Processing';
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
