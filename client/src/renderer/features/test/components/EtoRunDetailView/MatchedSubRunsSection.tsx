import { MatchedSubRun } from '../../types';

interface MatchedSubRunsSectionProps {
  subRuns: MatchedSubRun[];
  onViewDetails: (subRunId: number) => void;
  onReprocess: (subRunId: number) => void;
  onSkip: (subRunId: number) => void;
}

type SubRunStatus = 'success' | 'failure' | 'needs_template' | 'processing' | 'skipped';

function getStatusColor(status: SubRunStatus): string {
  switch (status) {
    case 'success':
      return 'text-green-400 bg-green-400/10';
    case 'processing':
      return 'text-blue-400 bg-blue-400/10';
    case 'failure':
      return 'text-red-400 bg-red-400/10';
    case 'needs_template':
      return 'text-yellow-400 bg-yellow-400/10';
    default:
      return 'text-gray-400 bg-gray-400/10';
  }
}

function getStatusIcon(status: SubRunStatus): string {
  switch (status) {
    case 'success':
      return '✓';
    case 'failure':
      return '✗';
    case 'needs_template':
      return '!';
    case 'processing':
      return '⟳';
    default:
      return '◦';
  }
}

export function MatchedSubRunsSection({
  subRuns,
  onViewDetails,
  onReprocess,
  onSkip,
}: MatchedSubRunsSectionProps) {
  if (subRuns.length === 0) return null;

  const successCount = subRuns.filter(sr => sr.status === 'success').length;
  const failureCount = subRuns.filter(sr => sr.status === 'failure').length;

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white">Matched Templates ({subRuns.length})</h2>
        <span className="text-gray-400 text-sm">
          {successCount} successful, {failureCount} failed
        </span>
      </div>

      <div className="space-y-3">
        {subRuns.map((subRun) => (
          <div
            key={subRun.id}
            className={`rounded-lg p-4 border transition-colors ${
              subRun.status === 'failure'
                ? 'bg-red-900/10 border-red-700/50 hover:border-red-600'
                : 'bg-gray-700/30 border-gray-700 hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${getStatusColor(subRun.status)}`}>
                  {getStatusIcon(subRun.status)}
                </span>
                <h3 className="text-white font-semibold">
                  Pages {subRun.pages.join(', ')} • {subRun.template.name}
                </h3>
              </div>

              <div className="flex gap-2">
                {subRun.status === 'success' && (
                  <button
                    onClick={() => onViewDetails(subRun.id)}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                  >
                    View Details
                  </button>
                )}
                {subRun.status === 'failure' && (
                  <>
                    <button
                      onClick={() => onViewDetails(subRun.id)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                    >
                      View Details
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
                  </>
                )}
              </div>
            </div>

            {subRun.status === 'success' && subRun.extractedData && (
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm ml-11">
                {Object.entries(subRun.extractedData).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <span className="text-gray-500 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}:</span>
                    <span className="text-gray-300">{value}</span>
                  </div>
                ))}
              </div>
            )}

            {subRun.status === 'failure' && subRun.errorMessage && (
              <div className="p-3 bg-red-900/20 border border-red-700/30 rounded text-sm">
                <p className="text-red-300">{subRun.errorMessage}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
