import { EtoPdfInfo, PageStatus as PageStatusType, EtoSubRunStatus } from '../../types';

interface EtoRunDetailSidebarProps {
  pdf: EtoPdfInfo;
  sourceDate: string;
  pageStatuses: PageStatusType[];
  hasFailedRuns: boolean;
  hasNeedsTemplate: boolean;
  onViewPdf: () => void;
  onReprocessAll: () => void;
  onSkipAll: () => void;
  onDelete: () => void;
}

function getStatusColor(status: EtoSubRunStatus): string {
  switch (status) {
    case 'success':
      return 'text-green-400 bg-green-400/10';
    case 'failure':
      return 'text-red-400 bg-red-400/10';
    case 'needs_template':
      return 'text-yellow-400 bg-yellow-400/10';
    case 'skipped':
      return 'text-gray-400 bg-gray-400/10';
    case 'processing':
      return 'text-blue-400 bg-blue-400/10';
    case 'not_started':
    default:
      return 'text-gray-500 bg-gray-500/10';
  }
}

function formatFileSize(bytes: number | null): string {
  if (bytes === null) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function EtoRunDetailSidebar({
  pdf,
  sourceDate,
  pageStatuses,
  hasFailedRuns,
  hasNeedsTemplate,
  onViewPdf,
  onReprocessAll,
  onSkipAll,
  onDelete,
}: EtoRunDetailSidebarProps) {
  const hasNonSuccessRuns = hasFailedRuns || hasNeedsTemplate;

  // Build a map of page number -> status for quick lookup
  const pageStatusMap = new Map(
    pageStatuses.map(ps => [ps.page_number, ps.status])
  );

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
            <p className="text-white">{formatFileSize(pdf.file_size)}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Total Pages</p>
            <p className="text-white">{pdf.page_count}</p>
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
          {Array.from({ length: pdf.page_count }, (_, i) => {
            const pageNum = i + 1;
            const status = pageStatusMap.get(pageNum) || 'not_started';

            return (
              <div
                key={pageNum}
                className={`w-10 h-10 flex items-center justify-center rounded text-sm font-semibold ${getStatusColor(status)}`}
                title={status}
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
