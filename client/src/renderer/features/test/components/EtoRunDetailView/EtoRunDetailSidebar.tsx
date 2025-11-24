import { EtoRunDetail, EtoRunMasterStatus, MatchedSubRun, NeedsTemplateSubRun, SkippedSubRun } from '../../types';

interface EtoRunDetailSidebarProps {
  totalPages: number;
  fileSize: string;
  sourceDate: string;
  hasFailedRuns: boolean;
  hasNeedsTemplate: boolean;
  matchedSubRuns: MatchedSubRun[];
  needsTemplateSubRuns: NeedsTemplateSubRun[];
  skippedSubRuns: SkippedSubRun[];
  onViewPdf: () => void;
  onReprocessAll: () => void;
  onSkipAll: () => void;
  onDelete: () => void;
}

type PageStatus = 'success' | 'failure' | 'needs_template' | 'skipped' | 'unprocessed';

function getStatusColor(status: PageStatus): string {
  switch (status) {
    case 'success':
      return 'text-green-400 bg-green-400/10';
    case 'failure':
      return 'text-red-400 bg-red-400/10';
    case 'needs_template':
      return 'text-yellow-400 bg-yellow-400/10';
    case 'skipped':
      return 'text-gray-400 bg-gray-400/10';
    default:
      return 'text-gray-500 bg-gray-500/10';
  }
}

export function EtoRunDetailSidebar({
  totalPages,
  fileSize,
  sourceDate,
  hasFailedRuns,
  hasNeedsTemplate,
  matchedSubRuns,
  needsTemplateSubRuns,
  skippedSubRuns,
  onViewPdf,
  onReprocessAll,
  onSkipAll,
  onDelete,
}: EtoRunDetailSidebarProps) {
  const hasNonSuccessRuns = hasFailedRuns || hasNeedsTemplate;

  // Helper to find page status
  const getPageStatus = (pageNum: number): { status: PageStatus; tooltip: string } => {
    const matchedSubRun = matchedSubRuns.find(sr => sr.pages.includes(pageNum));
    const needsTemplateSubRun = needsTemplateSubRuns.find(sr => sr.pages.includes(pageNum));
    const skippedSubRun = skippedSubRuns.find(sr => sr.pages.includes(pageNum));

    if (matchedSubRun) {
      return {
        status: matchedSubRun.status,
        tooltip: matchedSubRun.template.name,
      };
    }
    if (needsTemplateSubRun) {
      return {
        status: 'needs_template',
        tooltip: 'No template',
      };
    }
    if (skippedSubRun) {
      return {
        status: 'skipped',
        tooltip: 'Skipped',
      };
    }
    return {
      status: 'unprocessed',
      tooltip: 'Unprocessed',
    };
  };

  return (
    <div className="space-y-6">
      {/* Quick Actions */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Actions</h2>
        <div className="space-y-2">
          <button
            onClick={onViewPdf}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-semibold transition-colors"
          >
            View PDF
          </button>
          <button
            onClick={onReprocessAll}
            disabled={!hasNonSuccessRuns}
            className={`w-full px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              hasNonSuccessRuns
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }`}
          >
            Reprocess All
          </button>
          <button
            onClick={onSkipAll}
            disabled={!hasNonSuccessRuns}
            className={`w-full px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              hasNonSuccessRuns
                ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }`}
          >
            Skip All
          </button>
          <button
            onClick={onDelete}
            className="w-full px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-md text-sm transition-colors"
          >
            Delete Run
          </button>
        </div>
      </div>

      {/* File Information */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">File Information</h2>
        <div className="space-y-3">
          <div>
            <p className="text-gray-400 text-sm">File Size</p>
            <p className="text-white">{fileSize}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Total Pages</p>
            <p className="text-white">{totalPages}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Received</p>
            <p className="text-white">{sourceDate}</p>
          </div>
        </div>
      </div>

      {/* Page Breakdown */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Page Breakdown</h2>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: totalPages }, (_, i) => {
            const pageNum = i + 1;
            const { status, tooltip } = getPageStatus(pageNum);

            return (
              <div
                key={pageNum}
                className={`w-10 h-10 flex items-center justify-center rounded text-sm font-semibold ${getStatusColor(status)}`}
                title={tooltip}
              >
                {pageNum}
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-3 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-green-400/10"></div>
            <span className="text-gray-400">Success</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-red-400/10"></div>
            <span className="text-gray-400">Failed</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-yellow-400/10"></div>
            <span className="text-gray-400">Needs Template</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-gray-400/10"></div>
            <span className="text-gray-400">Skipped</span>
          </div>
        </div>
      </div>
    </div>
  );
}
