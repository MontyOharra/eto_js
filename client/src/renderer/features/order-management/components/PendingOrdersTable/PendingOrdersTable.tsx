/**
 * PendingOrdersTable Component
 *
 * Displays pending orders in a table format with TanStack Table.
 */

import { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
  CellContext,
} from '@tanstack/react-table';
import type { PendingOrderListItem } from '../../types';
import { OrderStatusBadge } from '../OrderStatusBadge';
import { FieldStatusBadge } from '../FieldStatusBadge';

// ============================================================================
// Types
// ============================================================================

interface PendingOrdersTableProps {
  data: PendingOrderListItem[];
  onRowClick: (orderId: number) => void;
  onViewHistory: (hawb: string) => void;
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

// ============================================================================
// Cell Components
// ============================================================================

const columnHelper = createColumnHelper<PendingOrderListItem>();

function HawbCell({ row }: CellContext<PendingOrderListItem, unknown>) {
  const data = row.original;
  const isComplete = data.status === 'created';

  return (
    <div className="flex flex-col gap-0.5">
      <span
        className={`font-mono text-sm font-semibold ${
          isComplete ? 'text-green-400' : 'text-white'
        }`}
      >
        {data.hawb}
      </span>
      {data.htc_order_number && (
        <span className="text-xs text-gray-500">
          Order #{data.htc_order_number}
        </span>
      )}
    </div>
  );
}

function CustomerCell({ row }: CellContext<PendingOrderListItem, unknown>) {
  const data = row.original;

  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-sm text-gray-300">{data.customer_name}</span>
      <span className="text-xs text-gray-500">ID: {data.customer_id}</span>
    </div>
  );
}

function StatusCell({ row }: CellContext<PendingOrderListItem, unknown>) {
  const data = row.original;

  return (
    <div className="flex flex-col gap-1.5">
      <OrderStatusBadge status={data.status} />
      <FieldStatusBadge fieldStatus={data.field_status} />
    </div>
  );
}

function ContributorsCell({ row }: CellContext<PendingOrderListItem, unknown>) {
  const data = row.original;

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-400">
        {data.contributing_run_count} run{data.contributing_run_count !== 1 ? 's' : ''}
      </span>
    </div>
  );
}

function ActionsCell({
  row,
  onViewHistory,
}: CellContext<PendingOrderListItem, unknown> & {
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

export function PendingOrdersTable({
  data,
  onRowClick,
  onViewHistory,
}: PendingOrdersTableProps) {
  const columns = useMemo(
    () => [
      columnHelper.display({
        id: 'hawb',
        header: 'HAWB',
        cell: HawbCell,
        size: 160,
        minSize: 120,
      }),
      columnHelper.display({
        id: 'customer',
        header: 'Customer',
        cell: CustomerCell,
        size: 180,
        minSize: 140,
      }),
      columnHelper.display({
        id: 'status',
        header: 'Status',
        cell: StatusCell,
        size: 180,
        minSize: 140,
      }),
      columnHelper.display({
        id: 'contributors',
        header: 'Contributors',
        cell: ContributorsCell,
        size: 120,
        minSize: 100,
      }),
      columnHelper.accessor('updated_at', {
        header: 'Last Updated',
        cell: ({ getValue }) => (
          <span className="text-sm text-gray-400" title={formatDate(getValue())}>
            {formatRelativeTime(getValue())}
          </span>
        ),
        size: 130,
        minSize: 100,
      }),
      columnHelper.accessor('created_at', {
        header: 'Created',
        cell: ({ getValue }) => (
          <span className="text-sm text-gray-400" title={formatDate(getValue())}>
            {formatRelativeTime(getValue())}
          </span>
        ),
        size: 130,
        minSize: 100,
      }),
      columnHelper.display({
        id: 'actions',
        header: () => <span className="text-right block">Actions</span>,
        cell: (props) => <ActionsCell {...props} onViewHistory={onViewHistory} />,
        size: 120,
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
              No pending orders found
            </div>
          ) : (
            <table className="w-full table-fixed">
              <tbody>
                {table.getRowModel().rows.map((row, index) => {
                  const isIncomplete = row.original.status === 'incomplete';
                  const isReady = row.original.status === 'ready';

                  // Background styling based on status
                  let rowBg = '';
                  if (isIncomplete) {
                    rowBg = 'bg-yellow-900/5';
                  } else if (isReady) {
                    rowBg = 'bg-blue-900/5';
                  }

                  return (
                    <tr
                      key={row.id}
                      onClick={() => onRowClick(row.original.id)}
                      className={`hover:bg-gray-700/30 transition-colors cursor-pointer ${rowBg} ${
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
