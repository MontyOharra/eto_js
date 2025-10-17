/**
 * TemplateBuilderHeader
 * Header section with static title and close button
 */

interface TemplateBuilderHeaderProps {
  pdfFileName: string;
  onClose: () => void;
}

export function TemplateBuilderHeader({
  pdfFileName,
  onClose,
}: TemplateBuilderHeaderProps) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
      <div className="flex-1 min-w-0">
        <h2 className="text-xl font-semibold text-white">
          Template Builder
        </h2>
        <p className="text-sm text-gray-400 truncate">{pdfFileName}</p>
      </div>

      <button
        onClick={onClose}
        className="ml-4 p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-800"
        aria-label="Close"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
