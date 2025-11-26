import { EtoRunListItem } from '../../types';
import { ProcessingStepBadge } from './ProcessingStepBadge';
import { formatFileSize, formatTimestampShort } from '../../../../shared/utils/formatUtils';

interface BaseEtoRunRowProps {
  run: EtoRunListItem;
  children?: React.ReactNode;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function BaseEtoRunRow({ run, children, isSelected = false, onToggleSelect }: BaseEtoRunRowProps) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors">
      <div className="flex items-center justify-between">
        {/* Left side - Checkbox + File info */}
        <div className="flex items-center space-x-4 flex-1">
          {/* Selection checkbox (replaces status icon) */}
          <div className="flex-shrink-0">
            {onToggleSelect && (
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggleSelect(run.id)}
                onClick={(e) => e.stopPropagation()}
                className="w-4 h-4 rounded border-2 border-gray-600 bg-gray-900 appearance-none checked:bg-blue-600 checked:border-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 cursor-pointer transition-colors relative checked:after:content-['✓'] checked:after:absolute checked:after:text-white checked:after:text-xs checked:after:left-[2px] checked:after:top-[-2px]"
              />
            )}
          </div>

          {/* File information */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-3">
              <h4 className="text-sm font-medium text-blue-300 truncate">
                {run.pdf.original_filename}
              </h4>
              {run.processing_step && ['processing', 'failure'].includes(run.status) && (
                <ProcessingStepBadge step={run.processing_step} />
              )}
            </div>

            {/* Metadata row */}
            <div className="mt-1 flex items-center space-x-4 text-xs text-gray-400">
              {run.started_at && (
                <span>Started: {formatTimestampShort(run.started_at)}</span>
              )}
              <span>
                From:{' '}
                {run.source.type === 'email' && run.source.sender_email
                  ? run.source.sender_email
                  : 'Manual Upload'}
              </span>
              <span>Size: {formatFileSize(run.pdf.file_size)}</span>
              {run.completed_at && (
                <span>Completed: {formatTimestampShort(run.completed_at)}</span>
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
