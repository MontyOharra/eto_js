/**
 * EtoRunDetailFooter
 * Footer section for ETO run detail with timestamps and close button
 */

import { formatTimestamp } from '../../../../shared/utils/formatUtils';
import type { EtoRunDetail } from '../../types';

interface EtoRunDetailFooterProps {
  runDetail: EtoRunDetail | null;
  onClose: () => void;
}

export function EtoRunDetailFooter({
  runDetail,
  onClose,
}: EtoRunDetailFooterProps) {
  return (
    <div className="flex items-center justify-between p-3 border-t border-gray-700 flex-shrink-0">
      {runDetail && (
        <div className="flex items-center space-x-4 text-xs text-gray-400">
          <div>
            <span className="text-gray-500">Started:</span>{" "}
            <span className="font-mono">
              {formatTimestamp(runDetail.started_at)}
            </span>
          </div>
          {runDetail.completed_at && (
            <div>
              <span className="text-gray-500">Completed:</span>{" "}
              <span className="font-mono">
                {formatTimestamp(runDetail.completed_at)}
              </span>
            </div>
          )}
        </div>
      )}
      <button
        type="button"
        onClick={onClose}
        className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-800 transition-colors text-sm"
      >
        Close
      </button>
    </div>
  );
}
