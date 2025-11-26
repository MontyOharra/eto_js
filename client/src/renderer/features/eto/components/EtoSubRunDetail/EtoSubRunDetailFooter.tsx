/**
 * EtoSubRunDetailFooter
 * Footer section for ETO run detail with timestamps, action buttons, and close button
 */

import { formatTimestamp } from '../../../../shared/utils/formatUtils';
import type { EtoSubRunFullDetail } from '../../types';

interface EtoSubRunDetailFooterProps {
  runDetail: EtoSubRunFullDetail | null;
  onClose: () => void;
  showActionButtons?: boolean;
  onReprocess?: () => void;
  onSkip?: () => void;
  isReprocessing?: boolean;
  isSkipping?: boolean;
}

export function EtoSubRunDetailFooter({
  runDetail,
  onClose,
  showActionButtons = false,
  onReprocess,
  onSkip,
  isReprocessing = false,
  isSkipping = false,
}: EtoSubRunDetailFooterProps) {
  const isProcessing = isReprocessing || isSkipping;

  return (
    <div className="flex items-center justify-between p-3 border-t border-gray-700 flex-shrink-0">
      {/* Left side - Timestamps */}
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

      {/* Right side - Action buttons */}
      <div className="flex items-center space-x-3">
        {showActionButtons && (
          <>
            <button
              type="button"
              onClick={onReprocess}
              disabled={isProcessing}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isReprocessing ? "Reprocessing..." : "Reprocess"}
            </button>
            <button
              type="button"
              onClick={onSkip}
              disabled={isProcessing}
              className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSkipping ? "Skipping..." : "Skip"}
            </button>
          </>
        )}
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-800 transition-colors text-sm"
        >
          Close
        </button>
      </div>
    </div>
  );
}
