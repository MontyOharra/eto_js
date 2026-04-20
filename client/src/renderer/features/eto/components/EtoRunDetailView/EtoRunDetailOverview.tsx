import { EtoRunStatus, EtoSource } from '../../types';

interface EtoRunDetailOverviewProps {
  source: EtoSource | undefined;
  status: EtoRunStatus;
}

function getStatusColor(status: EtoRunStatus): string {
  switch (status) {
    case 'success':
      return 'text-green-400 bg-green-400/10';
    case 'processing':
      return 'text-blue-400 bg-blue-400/10';
    case 'failure':
      return 'text-red-400 bg-red-400/10';
    case 'skipped':
      return 'text-yellow-400 bg-yellow-400/10';
    default:
      return 'text-gray-400 bg-gray-400/10';
  }
}

function getStatusLabel(status: EtoRunStatus): string {
  switch (status) {
    case 'success':
      return 'Completed';
    case 'processing':
      return 'Processing';
    case 'failure':
      return 'Failed';
    case 'skipped':
      return 'Skipped';
    default:
      return status;
  }
}

function formatLocalTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function EtoRunDetailOverview({
  source,
  status,
}: EtoRunDetailOverviewProps) {
  const isEmail = source?.type === 'email';
  const sourceLabel = isEmail ? `Email from ${source.sender_email}` : 'Manual Upload';
  const rawDate = isEmail ? source.received_at : source?.type === 'manual' ? source.created_at : '';
  const displayTime = rawDate ? formatLocalTime(rawDate) : '-';

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-semibold text-white mb-4">Overview</h2>
      <div className="grid grid-cols-3 gap-6">
        {/* Source */}
        <div>
          <p className="text-gray-400 text-sm">Source</p>
          <p className="text-white font-medium mt-1">{sourceLabel}</p>
          {isEmail && source?.type === 'email' && source.subject && (
            <p className="text-gray-500 text-xs mt-1 truncate" title={source.subject}>
              {source.subject}
            </p>
          )}
        </div>

        {/* Time */}
        <div>
          <p className="text-gray-400 text-sm">Received</p>
          <p className="text-white font-medium mt-1">{displayTime}</p>
        </div>

        {/* Status */}
        <div>
          <p className="text-gray-400 text-sm">Status</p>
          <div className="flex items-center gap-2 mt-1">
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(status)}`}>
              {getStatusLabel(status)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
