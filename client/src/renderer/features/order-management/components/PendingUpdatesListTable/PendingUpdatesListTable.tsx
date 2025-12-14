/**
 * PendingUpdatesListTable Component
 *
 * Displays pending updates in a flat list format (one row per HAWB),
 * similar to PendingOrdersTable. This replaces the old grouped-by-order view.
 */

import type { PendingUpdateListItem, PendingUpdateStatus } from '../../types';

interface PendingUpdatesListTableProps {
  data: PendingUpdateListItem[];
  onRowClick: (updateId: number) => void;
}

function formatRelativeTime(isoDate: string): string {
  try {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return isoDate;
  }
}

function getStatusBadge(status: PendingUpdateStatus) {
  switch (status) {
    case 'pending':
      return (
        <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
          Pending
        </span>
      );
    case 'approved':
      return (
        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
          Approved
        </span>
      );
    case 'rejected':
      return (
        <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded-full">
          Rejected
        </span>
      );
    case 'manual_review':
      return (
        <span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 text-xs rounded-full">
          Manual Review
        </span>
      );
    default:
      return (
        <span className="px-2 py-0.5 bg-gray-500/20 text-gray-400 text-xs rounded-full">
          {status}
        </span>
      );
  }
}

function getRowIndicator(update: PendingUpdateListItem) {
  // Icon indicator based on state (matching design spec from TODO.md)
  if (update.status === 'approved') {
    // Green checkmark - completed successfully
    return (
      <span className="text-green-500" title="Approved">
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }

  if (update.status === 'rejected') {
    // Gray X - rejected
    return (
      <span className="text-gray-500" title="Rejected">
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }

  // Pending status - check for conflicts
  if (update.conflict_count > 0) {
    // Yellow dot - needs user action (conflicts to resolve)
    return (
      <span className="w-3 h-3 rounded-full bg-yellow-500" title="Has conflicts to resolve" />
    );
  }

  // Pending with no conflicts - ready for review
  return (
    <span className="w-3 h-3 rounded-full bg-blue-500" title="Pending review" />
  );
}

export function PendingUpdatesListTable({
  data,
  onRowClick,
}: PendingUpdatesListTableProps) {
  if (data.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center text-gray-400">
        No pending updates found
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden h-full flex flex-col">
      <div className="overflow-auto flex-1">
        <table className="w-full">
          <thead className="bg-gray-750 sticky top-0">
            <tr className="text-xs text-gray-400 uppercase">
              <th className="px-4 py-3 text-left w-10"></th>
              <th className="px-4 py-3 text-left">HAWB</th>
              <th className="px-4 py-3 text-left">Customer</th>
              <th className="px-4 py-3 text-left">HTC Order #</th>
              <th className="px-4 py-3 text-left">Fields</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Updated</th>
            </tr>
          </thead>
          <tbody>
            {data.map((update) => (
              <tr
                key={update.id}
                onClick={() => onRowClick(update.id)}
                className={`border-b border-gray-700 hover:bg-gray-750 cursor-pointer transition-colors ${
                  update.status !== 'pending' ? 'opacity-60' : ''
                }`}
              >
                {/* Indicator */}
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center">
                    {getRowIndicator(update)}
                  </div>
                </td>

                {/* HAWB */}
                <td className="px-4 py-3">
                  <span className="text-white font-mono text-sm">
                    {update.hawb}
                  </span>
                </td>

                {/* Customer */}
                <td className="px-4 py-3">
                  <span className="text-gray-300 text-sm">
                    {update.customer_name || `Customer ${update.customer_id}`}
                  </span>
                </td>

                {/* HTC Order # */}
                <td className="px-4 py-3">
                  <span className="text-gray-300 text-sm font-mono">
                    {update.htc_order_number}
                  </span>
                </td>

                {/* Fields Info */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-300">
                      {update.fields_with_changes} field{update.fields_with_changes !== 1 ? 's' : ''}
                    </span>
                    {update.conflict_count > 0 && (
                      <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded">
                        {update.conflict_count} conflict{update.conflict_count !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </td>

                {/* Status */}
                <td className="px-4 py-3">
                  {getStatusBadge(update.status)}
                </td>

                {/* Updated */}
                <td className="px-4 py-3">
                  <span className="text-xs text-gray-400">
                    {formatRelativeTime(update.updated_at)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
