interface EtoRunDetailHeaderProps {
  pdfFilename: string;
  onBack: () => void;
}

export function EtoRunDetailHeader({ pdfFilename, onBack }: EtoRunDetailHeaderProps) {
  return (
    <div className="mb-6 flex items-center gap-4">
      <button
        onClick={onBack}
        className="text-gray-400 hover:text-gray-200 transition-colors flex-shrink-0"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div className="min-w-0 flex-1">
        <h1 className="text-3xl font-bold text-white break-words" title={pdfFilename}>
          {pdfFilename}
        </h1>
      </div>
    </div>
  );
}
