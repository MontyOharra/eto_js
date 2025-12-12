/**
 * OrderStatusBadge Component
 *
 * Displays the status of a pending order with appropriate styling.
 */

import type { PendingOrderStatus } from '../../types';

interface OrderStatusBadgeProps {
  status: PendingOrderStatus;
  className?: string;
}

const statusConfig: Record<PendingOrderStatus, { label: string; className: string }> = {
  incomplete: {
    label: 'Incomplete',
    className: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  },
  ready: {
    label: 'Ready',
    className: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  },
  processing: {
    label: 'Processing',
    className: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  },
  created: {
    label: 'Created',
    className: 'bg-green-500/20 text-green-400 border-green-500/30',
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-500/20 text-red-400 border-red-500/30',
  },
};

const defaultConfig = {
  label: 'Unknown',
  className: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

export function OrderStatusBadge({ status, className = '' }: OrderStatusBadgeProps) {
  const config = statusConfig[status] ?? defaultConfig;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.className} ${className}`}
    >
      {config.label}
    </span>
  );
}
