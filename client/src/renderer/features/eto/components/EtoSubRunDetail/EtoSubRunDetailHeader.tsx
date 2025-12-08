/**
 * EtoSubRunDetailHeader
 * Header section with title, status badge, view mode toggle, metadata, and close button
 */

import { EtoSubRunStatusBadge } from "./EtoSubRunStatusBadge";
import { formatDuration } from "../../../../shared/utils/formatUtils";
import type { EtoSubRunFullDetail } from "../../types";

type ViewMode = "summary" | "detail";

interface EtoSubRunDetailHeaderProps {
  runDetail: EtoSubRunFullDetail | undefined;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onClose: () => void;
}

export function EtoSubRunDetailHeader({
  runDetail,
  viewMode,
  onViewModeChange,
  onClose,
}: EtoSubRunDetailHeaderProps) {
  return (
    <div className="flex items-center justify-between p-3 border-b border-gray-700 flex-shrink-0">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-3">
          <h2 className="text-xl font-semibold text-white">ETO Run Details</h2>
          {runDetail && <EtoSubRunStatusBadge status={runDetail.status} />}
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center bg-gray-800 rounded-lg p-1 border-l border-gray-600 ml-4">
          <button
            onClick={() => onViewModeChange("summary")}
            className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
              viewMode === "summary"
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            Summary
          </button>
          <button
            onClick={() => onViewModeChange("detail")}
            className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
              viewMode === "detail"
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            Detail
          </button>
        </div>

        {runDetail && (
          <>
            {/* Pages */}
            <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
              <span className="text-gray-400">Pages:</span>{" "}
              <span className="font-mono">{runDetail.matched_pages.join(', ')}</span>
            </div>

            {/* Template */}
            {runDetail.template && (
              <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                <span className="text-gray-400">Template:</span>{" "}
                {runDetail.template.name}
                {runDetail.template.customer_name && (
                  <span className="text-gray-400 ml-1">({runDetail.template.customer_name})</span>
                )}
              </div>
            )}

            {/* Duration */}
            <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
              <span className="text-gray-400">Duration:</span>{" "}
              <span className="font-mono">
                {formatDuration(runDetail.started_at, runDetail.completed_at)}
              </span>
            </div>
          </>
        )}
      </div>

      <button
        onClick={onClose}
        className="text-gray-400 hover:text-gray-200 transition-colors"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}
