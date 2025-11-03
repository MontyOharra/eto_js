import { EtoRunListItem } from '../../types';
import { StatusIcon, StatusBadge, ProcessingStepBadge } from '../ui';

interface BaseEtoRunRowProps {
  run: EtoRunListItem;
  children?: React.ReactNode;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function BaseEtoRunRow({ run, children, isSelected = false, onToggleSelect }: BaseEtoRunRowProps) {
  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatBytes = (bytes: number | null) => {
    if (bytes === null) return 'Unknown';
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors">
      <div className="flex items-center justify-between">
        {/* Left side - Checkbox + File info */}
        <div className="flex items-center space-x-4 flex-1">
          {/* Selection checkbox (replaces status icon) */}
          <div className="flex-shrink-0">
            {onToggleSelect ? (
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggleSelect(run.id)}
                onClick={(e) => e.stopPropagation()}
                className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-800 cursor-pointer"
              />
            ) : (
              <StatusIcon status={run.status} />
            )}
          </div>

          {/* File information */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-3">
              <h4 className="text-sm font-medium text-blue-300 truncate">
                {run.pdf.original_filename}
              </h4>
              <StatusBadge status={run.status} />
              {run.processing_step && ['processing', 'failure'].includes(run.status) && (
                <ProcessingStepBadge step={run.processing_step} />
              )}
            </div>

            {/* Metadata row */}
            <div className="mt-1 flex items-center space-x-4 text-xs text-gray-400">
              {run.started_at && (
                <span>Started: {formatDate(run.started_at)}</span>
              )}
              <span>
                From:{' '}
                {run.source.type === 'email' && run.source.sender_email
                  ? run.source.sender_email
                  : 'Manual Upload'}
              </span>
              <span>Size: {formatBytes(run.pdf.file_size)}</span>
              {run.completed_at && (
                <span>Completed: {formatDate(run.completed_at)}</span>
              )}
              {run.matched_template && (
                <span>Template: {run.matched_template.template_name}</span>
              )}
            </div>

            {/* Error message */}
            {run.error_message && (
              <div className="mt-2 text-xs text-red-400">
                Error: {run.error_message}
              </div>
            )}
          </div>
        </div>

        {/* Right side - Action buttons slot */}
        {children && (
          <div className="flex items-center space-x-2">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}
