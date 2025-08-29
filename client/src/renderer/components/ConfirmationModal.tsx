import { createPortal } from "react-dom";

interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: "danger" | "warning" | "info";
}

export function ConfirmationModal({
  isOpen,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  onConfirm,
  onCancel,
  variant = "warning"
}: ConfirmationModalProps) {
  if (!isOpen) return null;

  const getVariantClasses = () => {
    switch (variant) {
      case "danger":
        return {
          icon: "text-red-400",
          confirmButton: "bg-red-600 hover:bg-red-700"
        };
      case "warning":
        return {
          icon: "text-yellow-400", 
          confirmButton: "bg-yellow-600 hover:bg-yellow-700"
        };
      case "info":
        return {
          icon: "text-blue-400",
          confirmButton: "bg-blue-600 hover:bg-blue-700"
        };
      default:
        return {
          icon: "text-yellow-400",
          confirmButton: "bg-yellow-600 hover:bg-yellow-700"
        };
    }
  };

  const classes = getVariantClasses();

  return createPortal(
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[10001]">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex items-center mb-4">
          <svg
            className={`w-6 h-6 ${classes.icon} mr-3`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
        </div>
        
        <p className="text-gray-300 mb-6">{message}</p>
        
        <div className="flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-medium text-white rounded transition-colors ${classes.confirmButton}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}