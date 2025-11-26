import { EtoSubRunSummary } from '../../types';

interface SkippedSubRunsSectionProps {
  subRuns: EtoSubRunSummary[];
  onReprocess: (subRunId: number) => void;
}

export function SkippedSubRunsSection({
  subRuns,
  onReprocess,
}: SkippedSubRunsSectionProps) {
  if (subRuns.length === 0) return null;

  const totalSkippedPages = subRuns.reduce((acc, sr) => acc + sr.matched_pages.length, 0);

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white">Skipped ({subRuns.length})</h2>
        <span className="text-gray-400 text-sm">
          {totalSkippedPages} pages skipped
        </span>
      </div>

      <div className="space-y-3">
        {subRuns.map((subRun) => (
          <div
            key={subRun.id}
            className="bg-gray-700/50 rounded-lg p-4 border border-gray-600 hover:border-gray-500 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-gray-400 bg-gray-400/10">
                  ⊘
                </span>
                <div>
                  <h3 className="text-white font-semibold">
                    Pages {subRun.matched_pages.join(', ')}
                  </h3>
                  <p className="text-gray-400 text-sm">Skipped by user</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => onReprocess(subRun.id)}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                >
                  Reprocess
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
