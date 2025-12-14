/**
 * UnifiedActionsTable Component
 *
 * Displays pending orders (creates) and pending updates in a single unified list.
 * Uses TanStack Table for consistent table structure.
 */

import { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
  CellContext,
} from '@tanstack/react-table';
import type { UnifiedActionListItem, ActionType } from '../../types';

// ============================================================================
// Types
// ============================================================================

interface UnifiedActionsTableProps {
  data: UnifiedActionListItem[];
  onRowClick: (type: ActionType, id: number) => void;
  onViewHistory: (hawb: string) => void;
  onToggleRead?: (type: ActionType, id: number, isRead: boolean) => void;
}

// ============================================================================
// Helpers
// ============================================================================

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

function formatRelativeTime(isoDate: string | null): string {
  if (!isoDate) return '-';
  try {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(isoDate);
  } catch {
    return isoDate;
  }
}

/**
 * Determine the indicator state for a row
 */
function getIndicatorState(item: UnifiedActionListItem): {
  color: 'yellow' | 'red' | 'blue' | 'green' | 'gray' | 'none';
  icon: 'dot' | 'check' | 'x' | 'none';
} {
  if (item.type === 'create') {
    // Create statuses: incomplete, ready, processing, created, failed
    if (item.status === 'failed') {
      return { color: 'red', icon: 'dot' };
    }
    if (item.status === 'created') {
      return { color: 'green', icon: 'check' };
    }
    if (item.conflict_count > 0) {
      return { color: 'yellow', icon: 'dot' };
    }
    if (!item.is_read) {
      return { color: 'blue', icon: 'dot' };
    }
    return { color: 'none', icon: 'none' };
  } else {
    // Update statuses: pending, approved, rejected
    if (item.status === 'approved') {
      return { color: 'green', icon: 'check' };
    }
    if (item.status === 'rejected') {
      return { color: 'gray', icon: 'x' };
    }
    // pending
    if (item.conflict_count > 0) {
      return { color: 'yellow', icon: 'dot' };
    }
    if (!item.is_read) {
      return { color: 'blue', icon: 'dot' };
    }
    return { color: 'yellow', icon: 'dot' }; // Pending updates always need action
  }
}

// ============================================================================
// Cell Components
// ============================================================================

const columnHelper = createColumnHelper<UnifiedActionListItem>();

function IndicatorCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const state = getIndicatorState(row.original);

  if (state.icon === 'none') {
    return <div className="w-4" />;
  }

  const colorClasses = {
    yellow: 'text-yellow-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
    green: 'text-green-400',
    gray: 'text-gray-400',
    none: '',
  };

  if (state.icon === 'dot') {
    return (
      <span className={`text-lg ${colorClasses[state.color]}`}>
        ●
      </span>
    );
  }

  if (state.icon === 'check') {
    return (
      <svg
        className={`w-4 h-4 ${colorClasses[state.color]}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    );
  }

  if (state.icon === 'x') {
    return (
      <svg
        className={`w-4 h-4 ${colorClasses[state.color]}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    );
  }

  return <div className="w-4" />;
}

function TypeCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const isCreate = row.original.type === 'create';

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase ${
        isCreate
          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
          : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
      }`}
    >
      {isCreate ? 'Create' : 'Update'}
    </span>
  );
}

function HawbCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const data = row.original;
  const isComplete =
    (data.type === 'create' && data.status === 'created') ||
    (data.type === 'update' && data.status === 'approved');

  return (
    <span
      className={`font-mono text-sm font-semibold ${
        isComplete ? 'text-green-400' : 'text-white'
      }`}
    >
      {data.hawb}
    </span>
  );
}

function CustomerCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  return (
    <span className="text-sm text-gray-300">{row.original.customer_name ?? '-'}</span>
  );
}

function OrderNumberCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const data = row.original;

  if (data.htc_order_number) {
    return (
      <span className="text-sm text-blue-400 font-medium">
        {data.htc_order_number}
      </span>
    );
  }

  return <span className="text-sm text-gray-500">-</span>;
}

function StatusInfoCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const data = row.original;

  if (data.type === 'create') {
    // Create: Show status + field progress + conflicts
    const statusColors: Record<string, string> = {
      incomplete: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      ready: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      processing: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
      created: 'bg-green-500/20 text-green-400 border-green-500/30',
      failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    };

    const requiredComplete =
      (data.required_fields_present ?? 0) >= (data.required_field_count ?? 1);

    return (
      <div className="flex flex-wrap items-center gap-2">
        {/* Status badge */}
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
            statusColors[data.status] ?? 'bg-gray-500/20 text-gray-400 border-gray-500/30'
          }`}
        >
          {data.status}
        </span>

        {/* Required fields progress */}
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
            requiredComplete
              ? 'bg-green-500/20 text-green-400 border-green-500/30'
              : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
          }`}
        >
          {data.required_fields_present ?? 0}/{data.required_field_count ?? 0} Req
        </span>

        {/* Conflict count */}
        {data.conflict_count > 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            {data.conflict_count}
          </span>
        )}

        {/* Error message for failed */}
        {data.status === 'failed' && data.error_message && (
          <span className="text-xs text-red-400 truncate max-w-[200px]" title={data.error_message}>
            {data.error_message}
          </span>
        )}
      </div>
    );
  } else {
    // Update: Show decision status + fields being changed
    const statusColors: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      approved: 'bg-green-500/20 text-green-400 border-green-500/30',
      rejected: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    };

    return (
      <div className="flex flex-wrap items-center gap-2">
        {/* Status badge */}
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
            statusColors[data.status] ?? 'bg-gray-500/20 text-gray-400 border-gray-500/30'
          }`}
        >
          {data.status}
        </span>

        {/* Fields being changed */}
        {data.fields_with_changes && data.fields_with_changes.length > 0 && (
          <span className="text-xs text-gray-400">
            {data.fields_with_changes.slice(0, 3).join(', ')}
            {data.fields_with_changes.length > 3 && ` +${data.fields_with_changes.length - 3}`}
          </span>
        )}

        {/* Conflict count */}
        {data.conflict_count > 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            {data.conflict_count}
          </span>
        )}
      </div>
    );
  }
}

function ActionsCell({
  row,
  onViewHistory,
}: CellContext<UnifiedActionListItem, unknown> & {
  onViewHistory: (hawb: string) => void;
}) {
  const data = row.original;

  return (
    <div className="flex items-center gap-1.5 justify-end">
      {/* View History button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onViewHistory(data.hawb);
        }}
        className="flex items-center gap-1 px-2 py-1 bg-blue-900/30 hover:bg-blue-700/50 text-blue-400 hover:text-blue-300 rounded transition-colors text-xs font-medium"
        title="View order history"
      >
        <svg
          className="w-3.5 h-3.5 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span className="hidden 2xl:inline whitespace-nowrap">History</span>
      </button>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function UnifiedActionsTable({
  data,
  onRowClick,
  onViewHistory,
  onToggleRead,
}: UnifiedActionsTableProps) {
  const columns = useMemo(
    () => [
      columnHelper.display({
        id: 'indicator',
        header: '',
        cell: IndicatorCell,
        size: 40,
        minSize: 40,
      }),
      columnHelper.display({
        id: 'type',
        header: 'Type',
        cell: TypeCell,
        size: 90,
        minSize: 80,
      }),
      columnHelper.display({
        id: 'hawb',
        header: 'HAWB',
        cell: HawbCell,
        size: 140,
        minSize: 120,
      }),
      columnHelper.display({
        id: 'customer',
        header: 'Customer',
        cell: CustomerCell,
        size: 160,
        minSize: 120,
      }),
      columnHelper.display({
        id: 'orderNumber',
        header: 'HTC Order #',
        cell: OrderNumberCell,
        size: 110,
        minSize: 90,
      }),
      columnHelper.display({
        id: 'statusInfo',
        header: 'Status / Info',
        cell: StatusInfoCell,
        size: 320,
        minSize: 200,
      }),
      columnHelper.accessor('updated_at', {
        header: 'Updated',
        cell: ({ getValue }) => (
          <span className="text-sm text-gray-400" title={formatDate(getValue())}>
            {formatRelativeTime(getValue())}
          </span>
        ),
        size: 100,
        minSize: 80,
      }),
      columnHelper.display({
        id: 'actions',
        header: () => <span className="text-right block">Actions</span>,
        cell: (props) => <ActionsCell {...props} onViewHistory={onViewHistory} />,
        size: 100,
        minSize: 80,
      }),
    ],
    [onViewHistory]
  );

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    columnResizeMode: 'onChange',
  });

  // Generate CSS variable styles for column widths
  const columnSizeVars = useMemo(() => {
    const headers = table.getFlatHeaders();
    const colSizes: Record<string, string> = {};

    const totalSize = headers.reduce((sum, header) => sum + header.getSize(), 0);

    for (const header of headers) {
      const percentage = (header.getSize() / totalSize) * 100;
      colSizes[`--header-${header.id}-size`] = `${percentage}%`;
      colSizes[`--col-${header.column.id}-size`] = `${percentage}%`;
    }
    return colSizes;
  }, [table.getState().columnSizing]);

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden flex flex-col h-full">
      {/* Table container with CSS variables for column sizes */}
      <div
        className="flex flex-col h-full"
        style={columnSizeVars as React.CSSProperties}
      >
        {/* Header */}
        <div className="py-4 bg-gray-750 border-b-2 border-gray-600 flex-shrink-0 overflow-y-scroll header-scrollbar-spacer">
          <style>{`
            .header-scrollbar-spacer::-webkit-scrollbar {
              width: 12px;
            }
            .header-scrollbar-spacer::-webkit-scrollbar-track {
              background: transparent;
            }
            .header-scrollbar-spacer::-webkit-scrollbar-thumb {
              background: transparent;
            }
          `}</style>
          <table className="w-full table-fixed">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-3 py-1 text-left text-gray-400 font-semibold text-sm uppercase first:pl-6 last:pr-6 overflow-hidden"
                      style={{ width: `var(--header-${header.id}-size)` }}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
          </table>
        </div>

        {/* Body - scrollable */}
        <div className="overflow-y-auto flex-1 custom-scrollbar">
          <style>{`
            .custom-scrollbar::-webkit-scrollbar {
              width: 12px;
            }
            .custom-scrollbar::-webkit-scrollbar-track {
              background: transparent;
              margin-top: 8px;
              margin-bottom: 8px;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb {
              background: rgb(75 85 99);
              border-radius: 6px;
              border: 3px solid rgb(31 41 55);
              background-clip: padding-box;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb:hover {
              background: rgb(107 114 128);
              background-clip: padding-box;
            }
          `}</style>

          {data.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-400">
              No pending actions found
            </div>
          ) : (
            <table className="w-full table-fixed">
              <tbody>
                {table.getRowModel().rows.map((row, index) => {
                  const item = row.original;

                  // Background styling based on state
                  let rowBg = '';
                  if (item.type === 'create') {
                    if (item.status === 'incomplete' || item.conflict_count > 0) {
                      rowBg = 'bg-yellow-900/5';
                    } else if (item.status === 'ready') {
                      rowBg = 'bg-blue-900/5';
                    } else if (item.status === 'failed') {
                      rowBg = 'bg-red-900/5';
                    }
                  } else {
                    if (item.status === 'pending') {
                      rowBg = item.conflict_count > 0 ? 'bg-yellow-900/5' : 'bg-purple-900/5';
                    }
                  }

                  // Unread styling
                  const unreadStyle = !item.is_read ? 'font-medium' : '';

                  return (
                    <tr
                      key={row.id}
                      onClick={() => onRowClick(item.type, item.id)}
                      className={`hover:bg-gray-700/30 transition-colors cursor-pointer ${rowBg} ${unreadStyle} ${
                        index < data.length - 1 ? 'border-b border-gray-700' : ''
                      }`}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td
                          key={cell.id}
                          className={`px-3 py-2.5 first:pl-6 last:pr-6 ${
                            cell.column.id === 'actions' ? '' : 'overflow-hidden'
                          }`}
                          style={{ width: `var(--col-${cell.column.id}-size)` }}
                        >
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
