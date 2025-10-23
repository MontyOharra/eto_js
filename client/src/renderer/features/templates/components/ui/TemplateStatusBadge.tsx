import { TemplateStatus } from '../../types';

interface TemplateStatusBadgeProps {
  status: TemplateStatus;
}

export function TemplateStatusBadge({ status }: TemplateStatusBadgeProps) {
  const statusConfig = {
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
