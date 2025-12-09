/**
 * PendingUpdatesTable Component
 *
 * Displays pending updates grouped by order, with approve/reject actions.
 */

import { useMemo, useState } from 'react';
import type { PendingUpdatesByOrder, PendingUpdateListItem } from '../../types';

interface PendingUpdatesTableProps {
  data: PendingUpdatesByOrder[];
  onApprove: (updateId: number) => void;
  onReject: (updateId: number) => void;
  onViewSubRun: (subRunId: number) => void;
  selectedIds: Set<number>;
  onSelectionChange: (ids: Set<number>) => void;
}

function formatDate(isoDate: string | null): string {
  if (!isoDate) return '-';
  try {
    const date = new Date(isoDate);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoDate;
  }
}

function formatFieldName(fieldName: string): string {
  return fieldName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

interface UpdateRowProps {
  update: PendingUpdateListItem;
  onApprove: (updateId: number) => void;
  onReject: (updateId: number) => void;
  onViewSubRun: (subRunId: number) => void;
  isSelected: boolean;
  onToggleSelect: (updateId: number) => void;
}

function UpdateRow({
  update,
  onApprove,
  onReject,
  onViewSubRun,
  isSelected,
  onToggleSelect,
}: UpdateRowProps) {
  const isPending = update.status === 'pending';

  return (
    <tr className={`border-b border-gray-700 ${isPending ? '' : 'opacity-50'}`}>
      {/* Checkbox */}
      <td className="px-3 py-2.5 w-12">
        {isPending && (
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(update.id)}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
          />
        )}
      </td>

      {/* Field */}
      <td className="px-3 py-2.5">
        <span className="text-sm text-white">{update.field_label}</span>
      </td>

      {/* Current Value */}
      <td className="px-3 py-2.5">
        <span className="text-sm text-gray-400 font-mono">
          {update.current_value || '(empty)'}
        </span>
      </td>

      {/* Arrow */}
      <td className="px-2 py-2.5 w-8">
        <svg
          className="w-4 h-4 text-gray-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 8l4 4m0 0l-4 4m4-4H3"
          />
        </svg>
      </td>

      {/* Proposed Value */}
      <td className="px-3 py-2.5">
        <span className="text-sm text-green-400 font-mono">
          {update.proposed_value}
        </span>
      </td>

      {/* Source */}
      <td className="px-3 py-2.5">
        {update.sub_run_id ? (
          <button
            onClick={() => onViewSubRun(update.sub_run_id!)}
            className="text-sm text-blue-400 hover:text-blue-300 hover:underline"
          >
            View Details
          </button>
        ) : (
          <span className="text-sm text-gray-500">-</span>
        )}
      </td>

      {/* Proposed At */}
      <td className="px-3 py-2.5">
        <span className="text-xs text-gray-400">
          {formatDate(update.proposed_at)}
        </span>
      </td>

      {/* Actions */}
      <td className="px-3 py-2.5">
        {isPending ? (
          <div className="flex items-center gap-1.5 justify-end">
            <button
              onClick={() => onApprove(update.id)}
              className="p-1.5 bg-green-900/30 hover:bg-green-700/50 text-green-400 hover:text-green-300 rounded transition-colors"
              title="Approve"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </button>
            <button
              onClick={() => onReject(update.id)}
              className="p-1.5 bg-red-900/30 hover:bg-red-700/50 text-red-400 hover:text-red-300 rounded transition-colors"
              title="Reject"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        ) : (
          <span
            className={`text-xs px-2 py-0.5 rounded ${
              update.status === 'approved'
                ? 'bg-green-500/20 text-green-400'
                : update.status === 'rejected'
                ? 'bg-red-500/20 text-red-400'
                : 'bg-gray-500/20 text-gray-400'
            }`}
          >
            {update.status}
          </span>
        )}
      </td>
    </tr>
  );
}

export function PendingUpdatesTable({
  data,
  onApprove,
  onReject,
  onViewSubRun,
  selectedIds,
  onSelectionChange,
}: PendingUpdatesTableProps) {
  const [expandedOrders, setExpandedOrders] = useState<Set<number>>(
    new Set(data.map((o) => o.htc_order_number))
  );

  const toggleOrder = (orderNumber: number) => {
    setExpandedOrders((prev) => {
      const next = new Set(prev);
      if (next.has(orderNumber)) {
        next.delete(orderNumber);
      } else {
        next.add(orderNumber);
      }
      return next;
    });
  };

  const toggleSelect = (updateId: number) => {
    const next = new Set(selectedIds);
    if (next.has(updateId)) {
      next.delete(updateId);
    } else {
      next.add(updateId);
    }
    onSelectionChange(next);
  };

  const toggleSelectAll = (updates: PendingUpdateListItem[]) => {
    const pendingIds = updates
      .filter((u) => u.status === 'pending')
      .map((u) => u.id);
    const allSelected = pendingIds.every((id) => selectedIds.has(id));

    const next = new Set(selectedIds);
    if (allSelected) {
      pendingIds.forEach((id) => next.delete(id));
    } else {
      pendingIds.forEach((id) => next.add(id));
    }
    onSelectionChange(next);
  };

  if (data.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center text-gray-400">
        No pending updates found
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {data.map((order) => {
        const isExpanded = expandedOrders.has(order.htc_order_number);
        const pendingCount = order.updates.filter(
          (u) => u.status === 'pending'
        ).length;

        return (
          <div
            key={order.htc_order_number}
            className="bg-gray-800 rounded-lg overflow-hidden"
          >
            {/* Order Header */}
            <div
              onClick={() => toggleOrder(order.htc_order_number)}
              className="px-4 py-3 bg-gray-750 flex items-center justify-between cursor-pointer hover:bg-gray-700 transition-colors"
            >
              <div className="flex items-center gap-4">
                <svg
                  className={`w-5 h-5 text-gray-400 transition-transform ${
                    isExpanded ? 'rotate-90' : ''
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
                <div>
                  <span className="text-white font-semibold">
                    Order #{order.htc_order_number}
                  </span>
                  <span className="text-gray-400 ml-2">({order.hawb})</span>
                </div>
                <span className="text-gray-500">{order.customer_name}</span>
              </div>
              <div className="flex items-center gap-3">
                {pendingCount > 0 && (
                  <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                    {pendingCount} pending
                  </span>
                )}
                <span className="text-sm text-gray-400">
                  {order.updates.length} update
                  {order.updates.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>

            {/* Updates Table */}
            {isExpanded && (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700 text-xs text-gray-400 uppercase">
                    <th className="px-3 py-2 w-12">
                      <input
                        type="checkbox"
                        checked={order.updates
                          .filter((u) => u.status === 'pending')
                          .every((u) => selectedIds.has(u.id))}
                        onChange={() => toggleSelectAll(order.updates)}
                        className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
                      />
                    </th>
                    <th className="px-3 py-2 text-left">Field</th>
                    <th className="px-3 py-2 text-left">Current</th>
                    <th className="px-2 py-2 w-8"></th>
                    <th className="px-3 py-2 text-left">Proposed</th>
                    <th className="px-3 py-2 text-left">Source</th>
                    <th className="px-3 py-2 text-left">Proposed At</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {order.updates.map((update) => (
                    <UpdateRow
                      key={update.id}
                      update={update}
                      onApprove={onApprove}
                      onReject={onReject}
                      onViewSubRun={onViewSubRun}
                      isSelected={selectedIds.has(update.id)}
                      onToggleSelect={toggleSelect}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        );
      })}
    </div>
  );
}
