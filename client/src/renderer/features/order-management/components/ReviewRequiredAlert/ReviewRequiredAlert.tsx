/**
 * ReviewRequiredAlert
 *
 * Modal alert displayed when an approve action returns requires_review=true.
 * This happens when the HTC state has changed since the action was created
 * (TOCTOU scenario).
 */

interface ReviewRequiredAlertProps {
  isOpen: boolean;
  actionType: 'create' | 'update';
  reviewReason: string | null;
  onClose: () => void;
}

export function ReviewRequiredAlert({
  isOpen,
  actionType,
  reviewReason,
  onClose,
}: ReviewRequiredAlertProps) {
  if (!isOpen) return null;

  // Format the action type for display
  const actionVerb = actionType === 'create' ? 'creation' : 'update';
  const actionVerbPast = actionType === 'create' ? 'created' : 'updated';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-lg w-full mx-4 border border-gray-700">
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-700">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-yellow-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-white">
            Review Required
          </h2>
        </div>

        {/* Content */}
        <div className="px-6 py-5">
          <p className="text-gray-300 leading-relaxed">
            The status of the order changed before the {actionVerb} was approved.
            This happened because another user may have {actionVerbPast} the order
            before ETO was approved to {actionType} it, and thus, the details of
            the order have changed.
          </p>
          <p className="text-gray-300 leading-relaxed mt-4">
            Please check the updated data to see what changed and approve again
            if everything is accurate.
          </p>

          {/* Show review reason for debugging/clarity */}
          {reviewReason && (
            <div className="mt-4 px-3 py-2 bg-gray-900/50 rounded border border-gray-700">
              <span className="text-xs text-gray-500 uppercase tracking-wide">
                Reason
              </span>
              <p className="text-sm text-gray-400 mt-1 font-mono">
                {reviewReason}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end px-6 py-4 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );
}
