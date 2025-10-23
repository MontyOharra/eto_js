import { PipelineStatus } from '../../types';

interface PipelineStatusBadgeProps {
  status: PipelineStatus;
}

export function PipelineStatusBadge({ status }: PipelineStatusBadgeProps) {
  const statusConfig = {
    draft: {
      text: 'Draft',
      classes: 'bg-gray-700 text-gray-300 border-gray-600',
    },
    active: {
      text: 'Active',
      classes: 'bg-green-900 text-green-300 border-green-700',
    },
    inactive: {
      text: 'Inactive',
      classes: 'bg-yellow-900 text-yellow-300 border-yellow-700',
    },
  };

  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.classes}`}
    >
      {config.text}
    </span>
  );
}
