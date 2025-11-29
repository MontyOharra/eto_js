interface EtoRunDetailHeaderProps {
  pdfFilename: string;
  onBack: () => void;
}

export function EtoRunDetailHeader({ pdfFilename, onBack }: EtoRunDetailHeaderProps) {
  return (
    <div className="mb-6 flex items-start gap-4 overflow-hidden">
      <button
        onClick={onBack}
        className="text-gray-400 hover:text-gray-200 transition-colors flex-shrink-0 mt-1"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div className="min-w-0 flex-1 overflow-hidden">
        <h1 className="text-3xl font-bold text-white break-all" title={pdfFilename}>
          {pdfFilename}
        </h1>
      </div>
    </div>
  );
}
