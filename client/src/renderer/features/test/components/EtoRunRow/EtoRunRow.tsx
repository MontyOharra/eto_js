import { EtoRunListItem, EtoRunStatus } from '../../types';

interface EtoRunRowProps {
  data: EtoRunListItem;
  onClick: () => void;
}

function getStatusColor(status: EtoRunStatus): string {
  switch (status) {
    case 'success':
      return 'text-green-400';
    case 'processing':
      return 'text-blue-400';
    case 'failure':
      return 'text-red-400';
    case 'skipped':
      return 'text-gray-400';
    default:
      return 'text-gray-400';
  }
}

// Helper to get source display text
function getSourceDisplay(source: EtoRunListItem['source']): string {
  if (source.type === 'email') {
    return source.sender_email;
  }
  return 'Manual Upload';
}

// Helper to get source subject (email only)
function getSourceSubject(source: EtoRunListItem['source']): string | null {
  if (source.type === 'email') {
    return source.subject;
  }
  return null;
}

// Helper to get source date
function getSourceDate(source: EtoRunListItem['source']): string | null {
  if (source.type === 'email') {
    return source.received_date;
  }
  return null;
}

// Helper to format date for display
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

export function EtoRunRow({ data, onClick }: EtoRunRowProps) {
  const { sub_runs_summary: summary } = data;

  const formatPageBreakdown = () => {
    if (summary.pages_matched_count === 0 && summary.pages_unmatched_count === 0) return '-';
    const parts = [];
    if (summary.pages_matched_count > 0) parts.push(`${summary.pages_matched_count} matched`);
    if (summary.pages_unmatched_count > 0) parts.push(`${summary.pages_unmatched_count} unmatched`);
    return parts.join(', ');
  };

  // Determine which indicators to show based on sub-run statuses
  const hasSubRuns = summary.success_count > 0 || summary.failure_count > 0 || summary.needs_template_count > 0;
  const showIndicators = hasSubRuns;

  const indicators = [];
  if (showIndicators) {
    if (summary.success_count > 0) {
      indicators.push({ color: 'green', ping: 'bg-green-400', solid: 'bg-green-500' });
    }
    if (summary.needs_template_count > 0) {
      indicators.push({ color: 'yellow', ping: 'bg-yellow-400', solid: 'bg-yellow-500' });
    }
    if (summary.failure_count > 0) {
      indicators.push({ color: 'red', ping: 'bg-red-400', solid: 'bg-red-500' });
    }
  }

  // Determine if row should be dimmed (read items)
  const isRead = data.is_read;
  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';

  // Determine if this is a failure row (parent-level failure)
  const isFailure = data.status === 'failure';
  const filenameColor = isFailure
    ? 'text-red-300'
    : (isRead ? 'text-gray-400' : 'text-gray-200');

  // Row background and border for failures
  const rowBg = isFailure ? 'bg-red-900/10 border-l-2 border-red-500/50' : '';

  // Determine which action buttons to show
  const isSkipped = data.status === 'skipped';
  const hasIssues = summary.failure_count > 0 || summary.needs_template_count > 0;
  const isFullySuccessful = data.status === 'success' && !hasIssues;

  // Skip button: Show if run has failures/needs_template (but not if already skipped)
  const showSkipButton = !isSkipped && (data.status === 'failure' || hasIssues);

  // Delete button: Only show for skipped runs (replaces skip button)
  const showDeleteButton = isSkipped;

  // Reprocess button: Show for anything except fully successful or skipped
  const showReprocessButton = !isFullySuccessful && !isSkipped;

  // Derived display values
  const sourceDisplay = getSourceDisplay(data.source);
  const sourceSubject = getSourceSubject(data.source);
  const sourceDate = formatDate(getSourceDate(data.source));
  const lastUpdated = formatDate(data.updated_at);

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      className={`w-full py-2.5 hover:bg-gray-700/30 transition-colors cursor-pointer text-left group ${rowBg}`}
    >
      <div className="px-6">
        <div className="grid gap-4" style={{ gridTemplateColumns: '2fr 2fr 1fr 100px 1fr auto 400px' }}>
        {/* PDF Filename with fixed-width indicator area */}
        <div className={`flex items-center gap-2 min-w-0 ${textOpacity}`}>
          {/* Fixed width area for indicators - always takes same space */}
          <div className="w-8 flex items-center gap-1 flex-shrink-0 self-center">
            {showIndicators && indicators.length > 0 && (
              <>
                {indicators.map((indicator, index) => (
                  <span key={index} className="relative flex h-2 w-2">
                    {/* Only show pulsing animation for unread items */}
                    {!isRead && (
                      <span className={`animate-ping absolute inset-0 rounded-full ${indicator.ping} opacity-75`}></span>
                    )}
                    <span className={`relative inline-flex rounded-full h-2 w-2 ${indicator.solid} ${isRead ? 'opacity-40' : ''}`}></span>
                  </span>
                ))}
              </>
            )}
          </div>
          <span className={`${filenameColor} text-sm ${!isRead ? 'font-medium' : ''} break-words min-w-0`}>{data.pdf.original_filename}</span>
        </div>

        {/* Source column with subject line below */}
        <div className={`flex flex-col gap-0.5 min-w-0 self-center ${textOpacity}`}>
          <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} break-words`}>
            {sourceDisplay}
          </span>
          {sourceSubject && (
            <span className={`text-xs ${isFailure ? 'text-red-200/50' : 'text-gray-500'} break-words`}>
              {sourceSubject}
            </span>
          )}
        </div>
        <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} break-words self-center ${textOpacity}`}>{sourceDate}</span>
        <span className={`text-sm font-semibold ${getStatusColor(data.status)} break-words self-center ${textOpacity}`}>
          {data.status.replace('_', ' ')}
        </span>
        <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} break-words self-center ${textOpacity}`}>{formatPageBreakdown()}</span>
        <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} break-words self-center ${textOpacity}`}>{lastUpdated}</span>

        {/* Action Buttons - Always visible, disabled when not applicable */}
        <div className="flex items-center gap-1.5 justify-end self-center">
          {/* Skip/Delete button - mutually exclusive */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (showDeleteButton) {
                // Handle delete action
              } else if (showSkipButton) {
                // Handle skip action
              }
            }}
            disabled={!showSkipButton && !showDeleteButton}
            className={`w-16 px-2 py-1 text-xs font-medium rounded transition-colors ${
              showDeleteButton
                ? 'bg-red-900/30 hover:bg-red-700/50 text-red-400 hover:text-red-300'
                : showSkipButton
                ? 'bg-yellow-900/30 hover:bg-yellow-700/50 text-yellow-400 hover:text-yellow-300'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
            title={
              showDeleteButton
                ? 'Delete this run'
                : showSkipButton
                ? 'Skip this run'
                : 'No action needed'
            }
          >
            {showDeleteButton ? 'Delete' : 'Skip'}
          </button>

          {/* Reprocess button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (showReprocessButton) {
                // Handle reprocess action
              }
            }}
            disabled={!showReprocessButton}
            className={`w-20 px-2 py-1 text-xs font-medium rounded transition-colors ${
              showReprocessButton
                ? 'bg-green-900/30 hover:bg-green-700/50 text-green-400 hover:text-green-300'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
            title={showReprocessButton ? 'Reprocess failed items' : 'No reprocessing needed'}
          >
            Reprocess
          </button>

          {/* View PDF button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              // Handle view PDF action
            }}
            className="w-20 px-2 py-1 text-xs font-medium bg-blue-900/30 hover:bg-blue-700/50 text-blue-400 hover:text-blue-300 rounded transition-colors whitespace-nowrap"
            title="View PDF"
          >
            View PDF
          </button>

          {/* Mark Read/Unread icon button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              // Handle mark read/unread toggle
            }}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-white"
            title={isRead ? 'Mark as unread' : 'Mark as read'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isRead ? (
                // Eye icon for read items
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              ) : (
                // Eye-slash icon for unread items
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              )}
            </svg>
          </button>
        </div>
        </div>
      </div>
    </div>
  );
}
