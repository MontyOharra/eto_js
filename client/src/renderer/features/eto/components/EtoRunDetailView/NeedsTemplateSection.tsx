import { EtoSubRunSummary } from '../../types';

interface NeedsTemplateSectionProps {
  subRuns: EtoSubRunSummary[];
  onBuildTemplate: (pageNumbers: number[]) => void;
  onReprocess: (subRunId: number) => void;
  onSkip: (subRunId: number) => void;
}

export function NeedsTemplateSection({
  subRuns,
  onBuildTemplate,
  onReprocess,
  onSkip,
}: NeedsTemplateSectionProps) {
  if (subRuns.length === 0) return null;

  const totalUnmatchedPages = subRuns.reduce((acc, sr) => acc + sr.matched_pages.length, 0);

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white">Needs Template ({subRuns.length})</h2>
        <span className="text-yellow-400 text-sm">
          {totalUnmatchedPages} pages unmatched
        </span>
      </div>

      <div className="space-y-3">
        {subRuns.map((subRun) => (
          <div
            key={subRun.id}
            className="bg-yellow-900/10 rounded-lg p-4 border border-yellow-700/50 hover:border-yellow-600 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-yellow-400 bg-yellow-400/10">
                  !
                </span>
                <div>
                  <h3 className="text-white font-semibold">
                    Pages {subRun.matched_pages.join(', ')}
                  </h3>
                  <p className="text-yellow-400 text-sm">No matching template found</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => onBuildTemplate(subRun.matched_pages)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                >
                  Build Template
                </button>
                <button
                  onClick={() => onReprocess(subRun.id)}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                >
                  Reprocess
                </button>
                <button
                  onClick={() => onSkip(subRun.id)}
                  className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                >
                  Skip
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
