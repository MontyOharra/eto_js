/**
 * EtoSubRunDetailFooter
 * Footer section for ETO run detail with timestamps, action buttons, and close button
 */

import { formatTimestamp } from '../../../../shared/utils/formatUtils';
import type { EtoSubRunFullDetail } from '../../types';

interface EtoSubRunDetailFooterProps {
  runDetail: EtoSubRunFullDetail | null;
  onClose: () => void;
  showReprocessButton?: boolean;
  showSkipButton?: boolean;
  onReprocess?: () => void;
  onSkip?: () => void;
  isReprocessing?: boolean;
  isSkipping?: boolean;
  /** Optional callback to navigate to the ETO runs page for this run */
  onViewInEto?: (etoRunId: number) => void;
  /** Optional callback to navigate to the matched template */
  onViewTemplate?: (templateId: number) => void;
}

export function EtoSubRunDetailFooter({
  runDetail,
  onClose,
  showReprocessButton = false,
  showSkipButton = false,
  onReprocess,
  onSkip,
  isReprocessing = false,
  isSkipping = false,
  onViewInEto,
  onViewTemplate,
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
        {showReprocessButton && (
          <button
            type="button"
            onClick={onReprocess}
            disabled={isProcessing}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isReprocessing ? "Reprocessing..." : "Reprocess"}
          </button>
        )}
        {showSkipButton && (
          <button
            type="button"
            onClick={onSkip}
            disabled={isProcessing}
            className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSkipping ? "Skipping..." : "Skip"}
          </button>
        )}
        {onViewInEto && runDetail?.eto_run_id && (
          <button
            type="button"
            onClick={() => onViewInEto(runDetail.eto_run_id)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors text-sm"
          >
            View in ETO
          </button>
        )}
        {onViewTemplate && runDetail?.template?.id && (
          <button
            type="button"
            onClick={() => onViewTemplate(runDetail.template!.id)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors text-sm"
          >
            View Template
          </button>
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
