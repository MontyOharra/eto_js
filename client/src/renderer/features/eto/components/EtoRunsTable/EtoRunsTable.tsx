import { useMemo, useEffect } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
  CellContext,
} from '@tanstack/react-table';
import { EtoRunListItem } from '../../types';

// ============================================================================
// Types
// ============================================================================

interface EtoRunsTableProps {
  data: EtoRunListItem[];
  onRowClick: (runId: number) => void;
  onReprocess: (runId: number) => void;
  onSkip: (runId: number) => void;
  onDelete: (runId: number) => void;
  onViewPdf: (pdfId: number, filename?: string) => void;
  onToggleRead: (runId: number, isRead: boolean) => void;
}

// ============================================================================
// Helpers
// ============================================================================

function getSourceDisplay(source: EtoRunListItem['source']): string {
  if (source.type === 'email') {
    return source.sender_email;
  }
  return 'Manual Upload';
}

function getSourceSubject(source: EtoRunListItem['source']): string | null {
  if (source.type === 'email') {
    return source.subject;
  }
  return null;
}

function getSourceDate(source: EtoRunListItem['source']): string {
  if (source.type === 'email') {
    return source.received_at;
  }
  return source.created_at;
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

// ============================================================================
// Cell Components
// ============================================================================

const columnHelper = createColumnHelper<EtoRunListItem>();

// Combined status cell showing processing state or page counts by status
function StatusCell({ row }: CellContext<EtoRunListItem, unknown>) {
  const data = row.original;
  const { sub_runs_summary: summary, sub_runs } = data;
  const isRead = data.is_read;
  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';

  // Processing state - show spinner
  if (data.status === 'processing' || data.status === 'not_started') {
    return (
      <div className={`flex items-center gap-2 ${textOpacity}`}>
        <svg className="animate-spin h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span className="text-blue-400 text-sm font-medium">Processing</span>
      </div>
    );
  }

  // Critical failure state
  if (data.status === 'failure') {
    return (
      <div className={`flex items-center gap-2 ${textOpacity}`}>
        <span className="text-red-400 text-sm font-semibold">Failed</span>
      </div>
    );
  }

  if (data.status === 'skipped') {
    return (
      <div className={`flex items-center gap-2 ${textOpacity}`}>
        <span className="text-gray-400 text-sm font-medium">Skipped</span>
      </div>
    );
  }

  // Calculate page counts by status from sub_runs array
  let successPages = 0;
  let needsTemplatePages = 0;
  let failurePages = 0;

  if (sub_runs && sub_runs.length > 0) {
    for (const subRun of sub_runs) {
      const pageCount = subRun.matched_pages?.length ?? 0;
      if (subRun.status === 'success') {
        successPages += pageCount;
      } else if (subRun.status === 'needs_template') {
        needsTemplatePages += pageCount;
      } else if (subRun.status === 'failure') {
        failurePages += pageCount;
      }
    }
  } else {
    // Fallback to summary counts if sub_runs not available
    // Use pages_unmatched_count for needs_template (accurate)
    // For success/failure, we can only approximate with sub-run counts
    needsTemplatePages = summary.pages_unmatched_count;
    // These are sub-run counts, not page counts - but better than nothing
    if (summary.success_count > 0 && summary.failure_count === 0) {
      successPages = summary.pages_matched_count;
    }
  }

  // Build indicators for non-zero counts
  const indicators = [];

  if (successPages > 0) {
    indicators.push({
      key: 'success',
      count: successPages,
      dotColor: 'bg-green-500',
      textColor: 'text-green-400',
      pingColor: 'bg-green-400',
    });
  }
  if (needsTemplatePages > 0) {
    indicators.push({
      key: 'needs_template',
      count: needsTemplatePages,
      dotColor: 'bg-yellow-500',
      textColor: 'text-yellow-400',
      pingColor: 'bg-yellow-400',
    });
  }
  if (failurePages > 0) {
    indicators.push({
      key: 'failure',
      count: failurePages,
      dotColor: 'bg-red-500',
      textColor: 'text-red-400',
      pingColor: 'bg-red-400',
    });
  }

  if (indicators.length === 0) {
    // No sub-runs yet or all skipped
    return <span className={`text-gray-500 text-sm ${textOpacity}`}>-</span>;
  }

  return (
    <div className={`flex items-center gap-3 ${textOpacity}`}>
      {indicators.map((indicator) => (
        <div key={indicator.key} className="flex items-center gap-1.5">
          <span className="relative flex h-2.5 w-2.5">
            {!isRead && (
              <span
                className={`sync-ping absolute inset-0 rounded-full ${indicator.pingColor}`}
              ></span>
            )}
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${indicator.dotColor} ${isRead ? 'opacity-50' : ''}`}></span>
          </span>
          <span className={`text-sm font-medium ${indicator.textColor} ${isRead ? 'opacity-70' : ''}`}>
            {indicator.count}
          </span>
        </div>
      ))}
    </div>
  );
}

// Filename cell (simplified - indicators moved to StatusCell)
function FilenameCell({ row }: CellContext<EtoRunListItem, unknown>) {
  const data = row.original;
  const isRead = data.is_read;
  const isFailure = data.status === 'failure';

  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';
  const filenameColor = isFailure
    ? 'text-red-300'
    : (isRead ? 'text-gray-400' : 'text-gray-200');

  return (
    <div className={`min-w-0 ${textOpacity}`}>
      <span className={`${filenameColor} text-sm ${!isRead ? 'font-medium' : ''} line-clamp-5 break-words`}>
        {data.pdf.original_filename}
      </span>
    </div>
  );
}

// Source cell with email and subject
function SourceCell({ row }: CellContext<EtoRunListItem, unknown>) {
  const data = row.original;
  const isRead = data.is_read;
  const isFailure = data.status === 'failure';
  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';

  const sourceDisplay = getSourceDisplay(data.source);
  const sourceSubject = getSourceSubject(data.source);

  return (
    <div className={`flex flex-col gap-0.5 min-w-0 ${textOpacity}`}>
      <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} line-clamp-3 break-words`}>
        {sourceDisplay}
      </span>
      {sourceSubject && (
        <span className={`text-xs ${isFailure ? 'text-red-200/50' : 'text-gray-500'} line-clamp-2 break-words`}>
          {sourceSubject}
        </span>
      )}
    </div>
  );
}

// Actions cell with buttons
function ActionsCell({
  row,
  onReprocess,
  onSkip,
  onDelete,
  onViewPdf,
  onToggleRead
}: CellContext<EtoRunListItem, unknown> & {
  onReprocess: (runId: number) => void;
  onSkip: (runId: number) => void;
  onDelete: (runId: number) => void;
  onViewPdf: (pdfId: number, filename?: string) => void;
  onToggleRead: (runId: number, isRead: boolean) => void;
}) {
  const data = row.original;
  const { sub_runs_summary: summary } = data;
  const isRead = data.is_read;
  const isSkipped = data.status === 'skipped';
  const hasIssues = summary.failure_count > 0 || summary.needs_template_count > 0;
  const isFullySuccessful = data.status === 'success' && !hasIssues;

  const showSkipButton = !isSkipped && (data.status === 'failure' || hasIssues);
  const showDeleteButton = isSkipped;
  const showReprocessButton = !isFullySuccessful && !isSkipped;

  return (
    <div className="flex items-center gap-1.5 justify-end flex-shrink-0 flex-wrap">
      {/* Skip/Delete button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (showDeleteButton) {
            onDelete(data.id);
          } else if (showSkipButton) {
            onSkip(data.id);
          }
        }}
        disabled={!showSkipButton && !showDeleteButton}
        className={`flex items-center gap-1 px-2 py-1 rounded transition-colors text-xs font-medium ${
          showDeleteButton
            ? 'bg-red-900/30 hover:bg-red-700/50 text-red-400 hover:text-red-300'
            : showSkipButton
            ? 'bg-yellow-900/30 hover:bg-yellow-700/50 text-yellow-400 hover:text-yellow-300'
            : 'bg-gray-800 text-gray-600 cursor-not-allowed'
        }`}
        title={showDeleteButton ? 'Delete this run' : showSkipButton ? 'Skip this run' : 'No action needed'}
      >
        {showDeleteButton ? (
          <>
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <span className="hidden 2xl:inline whitespace-nowrap">Delete</span>
          </>
        ) : (
          <>
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
            <span className="hidden 2xl:inline whitespace-nowrap">Skip</span>
          </>
        )}
      </button>

      {/* Reprocess button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (showReprocessButton) {
            onReprocess(data.id);
          }
        }}
        disabled={!showReprocessButton}
        className={`flex items-center gap-1 px-2 py-1 rounded transition-colors text-xs font-medium ${
          showReprocessButton
            ? 'bg-green-900/30 hover:bg-green-700/50 text-green-400 hover:text-green-300'
            : 'bg-gray-800 text-gray-600 cursor-not-allowed'
        }`}
        title={showReprocessButton ? 'Reprocess failed items' : 'No reprocessing needed'}
      >
        <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span className="hidden 2xl:inline whitespace-nowrap">Reprocess</span>
      </button>

      {/* View PDF button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onViewPdf(data.pdf.id, data.pdf.original_filename);
        }}
        className="flex items-center gap-1 px-2 py-1 bg-blue-900/30 hover:bg-blue-700/50 text-blue-400 hover:text-blue-300 rounded transition-colors text-xs font-medium"
        title="View PDF"
      >
        <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
        <span className="hidden 2xl:inline whitespace-nowrap">View PDF</span>
      </button>

      {/* Mark Read/Unread button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onToggleRead(data.id, !data.is_read);
        }}
        className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-white flex-shrink-0"
        title={isRead ? 'Mark as unread' : 'Mark as read'}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {isRead ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          )}
        </svg>
      </button>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function EtoRunsTable({
  data,
  onRowClick,
  onReprocess,
  onSkip,
  onDelete,
  onViewPdf,
  onToggleRead,
}: EtoRunsTableProps) {
  const columns = useMemo(() => [
    columnHelper.display({
      id: 'status',
      header: 'Status',
      cell: StatusCell,
      size: 140,
      minSize: 100,
    }),
    columnHelper.display({
      id: 'filename',
      header: 'PDF Filename',
      cell: FilenameCell,
      size: 300,
      minSize: 180,
    }),
    columnHelper.display({
      id: 'source',
      header: 'Source',
      cell: SourceCell,
      size: 220,
      minSize: 140,
    }),
    columnHelper.accessor((row) => getSourceDate(row.source), {
      id: 'received',
      header: 'Received',
      cell: ({ getValue, row }) => {
        const isRead = row.original.is_read;
        const isFailure = row.original.status === 'failure';
        const textOpacity = isRead ? 'opacity-60' : 'opacity-100';
        return (
          <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} ${textOpacity} break-words`}>
            {formatDate(getValue())}
          </span>
        );
      },
      size: 130,
      minSize: 100,
    }),
    columnHelper.accessor('last_processed_at', {
      header: 'Last Updated',
      cell: ({ getValue, row }) => {
        const isRead = row.original.is_read;
        const isFailure = row.original.status === 'failure';
        const textOpacity = isRead ? 'opacity-60' : 'opacity-100';
        return (
          <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} ${textOpacity} break-words`}>
            {formatDate(getValue())}
          </span>
        );
      },
      size: 130,
      minSize: 110,
    }),
    columnHelper.display({
      id: 'actions',
      header: () => <span className="text-right block">Actions</span>,
      cell: (props) => (
        <ActionsCell
          {...props}
          onReprocess={onReprocess}
          onSkip={onSkip}
          onDelete={onDelete}
          onViewPdf={onViewPdf}
          onToggleRead={onToggleRead}
        />
      ),
      size: 280,
      minSize: 140,
    }),
  ], [onReprocess, onSkip, onDelete, onViewPdf, onToggleRead]);

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

    // Calculate total width
    const totalSize = headers.reduce((sum, header) => sum + header.getSize(), 0);

    // Convert to percentages
    for (const header of headers) {
      const percentage = (header.getSize() / totalSize) * 100;
      colSizes[`--header-${header.id}-size`] = `${percentage}%`;
      colSizes[`--col-${header.column.id}-size`] = `${percentage}%`;
    }
    return colSizes;
  }, [table.getState().columnSizing]);

  // Synchronize all ping animations using the Web Animations API
  // When any syncPing animation starts, set its startTime to 0 so all animations are in phase
  useEffect(() => {
    const syncAnimations = (e: AnimationEvent) => {
      if (e.animationName === 'syncPing') {
        const target = e.target as Element;
        const anims = target.getAnimations();
        for (const anim of anims) {
          // Type guard for CSSAnimation which has animationName property
          if ('animationName' in anim && (anim as CSSAnimation).animationName === 'syncPing') {
            anim.startTime = 0;
          }
        }
      }
    };

    window.addEventListener('animationstart', syncAnimations as EventListener, true);
    return () => window.removeEventListener('animationstart', syncAnimations as EventListener, true);
  }, []);

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden flex flex-col h-full">
      {/* Global styles for synchronized animations */}
      <style>{`
        /* Synchronized ping animation - all indicators blink together */
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
            /* Hide scrollbar in header but maintain width */
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
                        : flexRender(header.column.columnDef.header, header.getContext())}
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
              No ETO runs found
            </div>
          ) : (
            <table className="w-full table-fixed">
              <tbody>
                {table.getRowModel().rows.map((row, index) => {
                  const isRead = row.original.is_read;
                  const isFailure = row.original.status === 'failure';

                  // Background styling
                  let rowBg = '';
                  if (isFailure) {
                    rowBg = 'bg-red-900/10 border-l-2 border-red-500/50';
                  } else if (!isRead) {
                    rowBg = 'bg-blue-900/10';
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
                          className={`px-3 py-2.5 first:pl-6 last:pr-6 ${cell.column.id === 'actions' ? '' : 'overflow-hidden'}`}
                          style={{ width: `var(--col-${cell.column.id}-size)` }}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
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
