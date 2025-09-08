import { EtoRunSummary, EtoDataTransforms } from "../../types/eto";

interface EtoRunRowProps {
  run: EtoRunSummary;
  onReview?: (runId: string) => void;
  onSkip?: (runId: string) => void;
  onView?: (runId: string) => void;
  onDelete?: (runId: string) => void;
  onReprocess?: (runId: string) => void;
  showButtons?: boolean;
}

export function EtoRunRow({ run, onReview, onSkip, onView, onDelete, onReprocess, showButtons = true }: EtoRunRowProps) {
  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusColor = (status: EtoRunSummary["status"]) => {
    return EtoDataTransforms.getStatusColorClass(status);
  };

  const getStatusIcon = (status: EtoRunSummary["status"]) => {
    switch (status) {
      case "success":
        return (
          <svg
            className="w-4 h-4 text-green-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "failure":
        return (
          <svg
            className="w-4 h-4 text-red-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "needs_template":
        return (
          <svg
            className="w-4 h-4 text-yellow-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "processing":
        return (
          <svg
            className="w-4 h-4 text-blue-400 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      case "not_started":
        return (
          <svg
            className="w-4 h-4 text-gray-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1-11a1 1 0 112 0v2h2a1 1 0 110 2h-2v2a1 1 0 11-2 0v-2H7a1 1 0 110-2h2V7z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "skipped":
        return (
          <svg
            className="w-4 h-4 text-gray-500"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z"
              clipRule="evenodd"
            />
            <path d="M4 4l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors">
      <div className="flex items-center justify-between">
        {/* Left side - File info and status */}
        <div className="flex items-center space-x-4 flex-1">
          {/* Status icon */}
          <div className="flex-shrink-0">{getStatusIcon(run.status)}</div>

          {/* File information */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-3">
              <h4 className="text-sm font-medium text-blue-300 truncate">
                {run.fileName}
              </h4>
              <span
                className={`text-xs font-medium ${getStatusColor(run.status)}`}
              >
                {EtoDataTransforms.getStatusDisplayName(run.status)}
              </span>
              {run.processing_step && (
                <span
                  className={`text-xs font-medium ${EtoDataTransforms.getProcessingStepColorClass(run.processing_step)}`}
                >
                  ({EtoDataTransforms.getProcessingStepDisplayName(run.processing_step)})
                </span>
              )}
            </div>

            <div className="mt-1 flex items-center space-x-4 text-xs text-gray-400">
              <span>Received: {formatDate(run.receivedAt)}</span>
              <span>From: {run.senderEmail}</span>
              <span>Size: {run.fileSizeFormatted}</span>
              {run.processingCompletedAt && (
                <span>Processed: {formatDate(run.processingCompletedAt)}</span>
              )}
              {run.matchedTemplateId && (
                <span>Template ID: {run.matchedTemplateId}</span>
              )}
            </div>

            {/* Error message for failures */}
            {run.errorMessage && (
              <div className="mt-2 text-xs text-red-400">
                Error: {run.errorMessage}
              </div>
            )}
          </div>
        </div>

        {/* Right side - Actions and review info */}
        <div className="flex items-center space-x-3">
          {/* Action buttons */}
          {showButtons && (
            <div className="flex space-x-2">
              {/* View button for successful extractions */}
              {run.status === "success" && onView && (
                <button
                  onClick={() => onView(run.id.toString())}
                  className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                >
                  View
                </button>
              )}
              
              {/* View and Review buttons for failed extractions */}
              {run.status === "failure" && (
                <>
                  {onView && (
                    <button
                      onClick={() => onView(run.id.toString())}
                      className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
                    >
                      View
                    </button>
                  )}
                  {onReview && (
                    <button
                      onClick={() => onReview(run.id.toString())}
                      className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
                    >
                      Review
                    </button>
                  )}
                  {onSkip && (
                    <button
                      onClick={() => onSkip(run.id.toString())}
                      className="px-3 py-1 text-xs bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors"
                    >
                      Skip
                    </button>
                  )}
                </>
              )}
              
              {/* Build Template and Skip buttons for needs_template */}
              {run.status === "needs_template" && (
                <>
                  {onReview && (
                    <button
                      onClick={() => onReview(run.id.toString())}
                      className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                    >
                      Build Template
                    </button>
                  )}
                  {onSkip && (
                    <button
                      onClick={() => onSkip(run.id.toString())}
                      className="px-3 py-1 text-xs bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors"
                    >
                      Skip
                    </button>
                  )}
                </>
              )}
              
              {/* Delete and Reprocess buttons for skipped runs */}
              {run.status === "skipped" && (
                <>
                  {onReprocess && (
                    <button
                      onClick={() => onReprocess(run.id.toString())}
                      className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                    >
                      Reprocess
                    </button>
                  )}
                  {onDelete && (
                    <button
                      onClick={() => onDelete(run.id.toString())}
                      className="px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                    >
                      Delete
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
