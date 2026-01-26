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
import { STATUS_COLORS } from '../../constants';

// ============================================================================
// Types
// ============================================================================

interface UnifiedActionsTableProps {
  data: UnifiedActionListItem[];
  onRowClick: (type: ActionType, id: number) => void;
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
  color: 'yellow' | 'red' | 'blue' | 'green' | 'gray' | 'orange' | 'none';
  icon: 'dot' | 'check' | 'x' | 'none';
} {
  // Status-based indicators (applies to all action types)
  if (item.status === 'failed') {
    return { color: 'red', icon: 'dot' };
  }
  if (item.status === 'ambiguous' || item.action_type === 'ambiguous') {
    return { color: 'red', icon: 'dot' };
  }
  if (item.status === 'rejected') {
    return { color: 'gray', icon: 'x' };
  }
  if (item.status === 'completed') {
    return { color: 'green', icon: 'check' };
  }
  if (item.status === 'conflict' || item.conflict_count > 0) {
    return { color: 'yellow', icon: 'dot' };
  }
  if (item.status === 'incomplete') {
    return { color: 'orange', icon: 'dot' };
  }
  if (!item.is_read) {
    return { color: 'blue', icon: 'dot' };
  }
  if (item.status === 'ready') {
    return { color: 'blue', icon: 'dot' };
  }
  return { color: 'none', icon: 'none' };
}

// ============================================================================
// Cell Components
// ============================================================================

const columnHelper = createColumnHelper<UnifiedActionListItem>();

function IndicatorCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const state = getIndicatorState(row.original);
  const isRead = row.original.is_read;

  if (state.icon === 'none') {
    return <div className="w-4" />;
  }

  const dotColors = {
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    gray: 'bg-gray-500',
    orange: 'bg-orange-500',
    none: '',
  };

  const pingColors = {
    yellow: 'bg-yellow-400',
    red: 'bg-red-400',
    blue: 'bg-blue-400',
    green: 'bg-green-400',
    gray: 'bg-gray-400',
    orange: 'bg-orange-400',
    none: '',
  };

  const iconColors = {
    yellow: 'text-yellow-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
    green: 'text-green-400',
    gray: 'text-gray-400',
    orange: 'text-orange-400',
    none: '',
  };

  if (state.icon === 'dot') {
    return (
      <span className="relative flex h-3 w-3">
        {!isRead && (
          <span
            className={`sync-ping absolute inset-0 rounded-full ${pingColors[state.color]}`}
          ></span>
        )}
        <span className={`relative inline-flex rounded-full h-3 w-3 ${dotColors[state.color]} ${isRead ? 'opacity-50' : ''}`}></span>
      </span>
    );
  }

  if (state.icon === 'check') {
    return (
      <svg
        className={`w-4 h-4 ${iconColors[state.color]} ${isRead ? 'opacity-50' : ''}`}
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
        className={`w-4 h-4 ${iconColors[state.color]} ${isRead ? 'opacity-50' : ''}`}
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
  const { action_type, status, is_read: isRead } = row.original;
  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';

  // Ambiguous action type gets red styling (like failed)
  if (action_type === 'ambiguous' || status === 'ambiguous') {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold uppercase ${textOpacity} bg-red-500/20 text-red-400 border border-red-500/30`}
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Ambiguous
      </span>
    );
  }

  // Neutral/muted type badges - context only, not action-oriented
  const isCreate = action_type === 'create';
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium uppercase ${textOpacity} ${
        isCreate
          ? 'bg-slate-600/30 text-slate-300 border border-slate-500/40'
          : 'bg-slate-700/40 text-slate-400 border border-slate-500/50'
      }`}
    >
      {isCreate ? (
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      ) : (
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      )}
      {isCreate ? 'Create' : 'Update'}
    </span>
  );
}

function HawbCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const data = row.original;
  const isRead = data.is_read;
  const isComplete = data.status === 'completed';

  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';
  const textColor = isComplete
    ? 'text-green-400'
    : isRead
      ? 'text-gray-400'
      : 'text-white';

  return (
    <span
      className={`font-mono text-sm ${textColor} ${textOpacity} ${!isRead ? 'font-semibold' : ''}`}
    >
      {data.hawb}
    </span>
  );
}

function CustomerCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const isRead = row.original.is_read;
  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';
  const textColor = isRead ? 'text-gray-400' : 'text-gray-300';

  return (
    <span className={`text-sm ${textColor} ${textOpacity}`}>{row.original.customer_name ?? '-'}</span>
  );
}

function OrderNumberCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const data = row.original;
  const isRead = data.is_read;
  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';

  if (data.htc_order_number) {
    return (
      <span className={`text-sm text-blue-400 ${textOpacity} ${!isRead ? 'font-medium' : ''}`}>
        {data.htc_order_number}
      </span>
    );
  }

  return <span className={`text-sm text-gray-500 ${textOpacity}`}>-</span>;
}

/**
 * Format field names for display - converts snake_case to Title Case
 */
function formatFieldName(fieldName: string): string {
  return fieldName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function StatusInfoCell({ row }: CellContext<UnifiedActionListItem, unknown>) {
  const data = row.original;
  const isRead = data.is_read;
  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';

  const requiredComplete = data.required_fields_present >= data.required_fields_total;
  const isUpdate = data.action_type === 'update';
  const isFailed = data.status === 'failed';

  return (
    <div className={`flex flex-wrap items-center gap-2 ${textOpacity}`}>
      {/* Status badge */}
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
          STATUS_COLORS[data.status] ?? 'bg-gray-500/20 text-gray-400 border-gray-500/30'
        }`}
      >
        {data.status}
      </span>

      {/* For failed status: show error message instead of normal info */}
      {isFailed && data.error_message && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border bg-red-500/20 text-red-400 border-red-500/30 max-w-md truncate">
          <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="truncate">{data.error_message}</span>
        </span>
      )}

      {/* Only show normal info if not failed */}
      {!isFailed && (
        <>
          {/* Conflict count - right after status */}
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

          {/* Error field count - shows fields that failed processing (hide for finalized actions) */}
          {data.error_field_count > 0 && data.status !== 'completed' && data.status !== 'rejected' && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border bg-red-500/20 text-red-400 border-red-500/30">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              {data.error_field_count} error{data.error_field_count > 1 ? 's' : ''}
            </span>
          )}

          {/* For updates: show comma-separated field names */}
          {isUpdate && data.field_names.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border bg-blue-500/20 text-blue-400 border-blue-500/30">
              {data.field_names.map(formatFieldName).join(', ')}
            </span>
          )}

          {/* For creates: show required/optional field counts */}
          {!isUpdate && (
            <>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
                  requiredComplete
                    ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                    : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
                }`}
              >
                {data.required_fields_present}/{data.required_fields_total} Required
              </span>

              {data.optional_fields_present > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border bg-gray-500/20 text-gray-400 border-gray-500/30">
                  {data.optional_fields_present}/{data.optional_fields_total} Optional
                </span>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function UnifiedActionsTable({
  data,
  onRowClick,
  onToggleRead,
}: UnifiedActionsTableProps) {
  const columns = useMemo(
    () => [
      columnHelper.display({
        id: 'indicator',
        header: '',
        cell: IndicatorCell,
        size: 36,
        minSize: 36,
      }),
      columnHelper.display({
        id: 'type',
        header: 'Type',
        cell: TypeCell,
        size: 80,
        minSize: 70,
      }),
      columnHelper.display({
        id: 'hawb',
        header: 'HAWB',
        cell: HawbCell,
        size: 110,
        minSize: 100,
      }),
      columnHelper.display({
        id: 'customer',
        header: 'Customer',
        cell: CustomerCell,
        size: 130,
        minSize: 100,
      }),
      columnHelper.display({
        id: 'orderNumber',
        header: 'HTC #',
        cell: OrderNumberCell,
        size: 80,
        minSize: 70,
      }),
      columnHelper.display({
        id: 'statusInfo',
        header: 'Status / Info',
        cell: StatusInfoCell,
        size: 450,
        minSize: 300,
      }),
      columnHelper.display({
        id: 'lastProcessed',
        header: 'Updated',
        cell: ({ row }) => {
          // Use last_processed_at if available, fall back to updated_at
          const timestamp = row.original.last_processed_at ?? row.original.updated_at;
          const isRead = row.original.is_read;
          const textOpacity = isRead ? 'opacity-60' : 'opacity-100';
          return (
            <span className={`text-sm text-gray-400 ${textOpacity}`} title={formatDate(timestamp)}>
              {formatRelativeTime(timestamp)}
            </span>
          );
        },
        size: 80,
        minSize: 70,
      }),
      columnHelper.display({
        id: 'actions',
        header: '',
        cell: ({ row }) => {
          const item = row.original;
          return (
            <div className="flex items-center justify-end">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleRead?.(item.action_type, item.id, !item.is_read);
                }}
                className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-white flex-shrink-0"
                title={item.is_read ? 'Mark as unread' : 'Mark as read'}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {item.is_read ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  )}
                </svg>
              </button>
            </div>
          );
        },
        size: 50,
        minSize: 40,
      }),
    ],
    [onToggleRead]
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
      {/* Global styles for synchronized ping animations */}
      <style>{`
        @keyframes syncPing {
          0% {
            transform: scale(1);
            opacity: 0.75;
          }
          100% {
            transform: scale(2.5);
            opacity: 0;
          }
        }
        .sync-ping {
          animation: syncPing 1500ms cubic-bezier(0, 0, 0.2, 1) infinite;
        }
      `}</style>

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
                  const isRead = item.is_read;

                  // Background styling based on status (not type)
                  let rowBg = '';
                  if (item.status === 'ambiguous' || item.action_type === 'ambiguous') {
                    rowBg = 'bg-red-900/10';
                  } else if (item.status === 'failed') {
                    rowBg = 'bg-red-900/10';
                  } else if (item.status === 'rejected') {
                    rowBg = 'bg-gray-900/10';
                  } else if (item.error_field_count > 0 && item.status !== 'completed') {
                    // Rows with field processing errors get a subtle red tint (not for finalized actions)
                    rowBg = 'bg-red-900/5';
                  } else if (item.status === 'conflict' || item.conflict_count > 0) {
                    rowBg = 'bg-yellow-900/5';
                  } else if (item.status === 'incomplete') {
                    rowBg = 'bg-orange-900/5';
                  } else if (item.status === 'ready') {
                    rowBg = 'bg-blue-900/5';
                  } else if (!isRead) {
                    rowBg = 'bg-blue-900/10';
                  }

                  const handleRowClick = () => {
                    if (item.status === 'ambiguous' || item.action_type === 'ambiguous') {
                      alert(
                        'Multiple orders associated with this HAWB and customer. Please check HTC and make manual updates.'
                      );
                      // Mark as read after user closes the popup
                      if (!item.is_read) {
                        onToggleRead?.(item.action_type, item.id, true);
                      }
                      return;
                    }
                    onRowClick(item.action_type, item.id);
                  };

                  return (
                    <tr
                      key={row.id}
                      onClick={handleRowClick}
                      className={`hover:bg-gray-700/30 transition-colors cursor-pointer ${rowBg} ${
                        index < data.length - 1 ? 'border-b border-gray-700' : ''
                      }`}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td
                          key={cell.id}
                          className="px-3 py-2.5 first:pl-6 last:pr-6 overflow-hidden"
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
