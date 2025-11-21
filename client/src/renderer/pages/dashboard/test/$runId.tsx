import { createFileRoute, useNavigate } from '@tanstack/react-router';

export const Route = createFileRoute('/dashboard/test/$runId')({
  component: EtoRunDetailPage,
});

// Mock data for a detailed ETO run
const mockEtoRunDetail = {
  id: 2,
  pdfFilename: 'receipts_jan_2024.pdf',
  source: 'Manual Upload',
  sourceDate: '2024-01-15 10:40:18',
  masterStatus: 'success',
  totalPages: 8,
  createdAt: '2024-01-15 10:45:32',
  lastUpdated: '2024-01-15 11:02:14',
  processingStep: 'sub_runs',

  // PDF file info
  pdfFile: {
    id: 123,
    storagePath: '/storage/uploads/receipts_jan_2024.pdf',
    fileSize: '2.4 MB',
  },

  // Email details (if from email)
  emailDetails: null, // Would be populated if source was email

  // Sub-runs breakdown
  subRuns: [
    {
      id: 1,
      pageStart: 1,
      pageEnd: 3,
      status: 'success',
      template: {
        id: 5,
        name: 'Vendor Receipt Template',
        description: 'Standard vendor receipt format',
      },
      extractedData: {
        vendor: 'ABC Supply Co.',
        total: '$1,245.67',
        date: '2024-01-10',
        invoiceNumber: 'INV-2024-001',
      },
      processedAt: '2024-01-15 10:52:08',
      errorMessage: null,
    },
    {
      id: 2,
      pageStart: 4,
      pageEnd: 5,
      status: 'success',
      template: {
        id: 5,
        name: 'Vendor Receipt Template',
        description: 'Standard vendor receipt format',
      },
      extractedData: {
        vendor: 'XYZ Hardware',
        total: '$842.33',
        date: '2024-01-12',
        invoiceNumber: 'INV-2024-045',
      },
      processedAt: '2024-01-15 10:58:22',
      errorMessage: null,
    },
    {
      id: 3,
      pageStart: 6,
      pageEnd: 8,
      status: 'needs_template',
      template: null,
      extractedData: null,
      processedAt: null,
      errorMessage: null,
    },
  ],

  // Actions/history log
  activityLog: [
    { timestamp: '2024-01-15 10:45:32', action: 'Run created', user: 'System' },
    { timestamp: '2024-01-15 10:45:35', action: 'Template matching started', user: 'System' },
    { timestamp: '2024-01-15 10:45:42', action: 'Found 2 template matches', user: 'System' },
    { timestamp: '2024-01-15 10:45:45', action: 'Sub-run processing started', user: 'System' },
    { timestamp: '2024-01-15 10:52:08', action: 'Sub-run 1 completed successfully', user: 'System' },
    { timestamp: '2024-01-15 10:58:22', action: 'Sub-run 2 completed successfully', user: 'System' },
    { timestamp: '2024-01-15 11:02:14', action: 'Run completed with 3 unmatched pages', user: 'System' },
  ],
};

function EtoRunDetailPage() {
  const { runId } = Route.useParams();
  const navigate = useNavigate();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-green-400 bg-green-400/10';
      case 'processing':
        return 'text-blue-400 bg-blue-400/10';
      case 'failure':
        return 'text-red-400 bg-red-400/10';
      case 'needs_template':
        return 'text-yellow-400 bg-yellow-400/10';
      case 'not_started':
        return 'text-gray-400 bg-gray-400/10';
      default:
        return 'text-gray-400 bg-gray-400/10';
    }
  };

  const getStatusIcon = (status: string) => {
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
  };

  return (
    <div className="p-6">
      {/* Header with back button */}
      <div className="mb-6 flex items-center gap-4">
        <button
          onClick={() => navigate({ to: '/dashboard/test' })}
          className="text-gray-400 hover:text-gray-200 transition-colors"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div>
          <h1 className="text-3xl font-bold text-white">{mockEtoRunDetail.pdfFilename}</h1>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        {/* Main content - 3 columns */}
        <div className="col-span-3 flex flex-col gap-6">
          {/* Overview Stats */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Overview</h2>
            <div className="grid grid-cols-5 gap-4">
              <div>
                <p className="text-gray-400 text-sm">Source</p>
                <p className="text-white font-medium mt-1">{mockEtoRunDetail.source}</p>
                <p className="text-gray-400 text-xs mt-1">{mockEtoRunDetail.sourceDate}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Status</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(mockEtoRunDetail.masterStatus)}`}>
                    {mockEtoRunDetail.masterStatus}
                  </span>
                </div>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Total Pages</p>
                <p className="text-white text-lg font-semibold mt-1">{mockEtoRunDetail.totalPages}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Templates Matched</p>
                <p className="text-white text-lg font-semibold mt-1">{mockEtoRunDetail.subRuns.filter(sr => sr.template).length}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Processing Time</p>
                <p className="text-white text-lg font-semibold mt-1">16m 42s</p>
              </div>
            </div>
          </div>

          {/* Sub-runs Section */}
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col min-h-0 flex-1">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Sub-runs ({mockEtoRunDetail.subRuns.length})</h2>
              <span className="text-gray-400 text-sm">
                {mockEtoRunDetail.subRuns.filter(sr => sr.status === 'needs_template').length} need attention
              </span>
            </div>

            <div className="space-y-3 overflow-y-auto pr-2 flex-1">
              {mockEtoRunDetail.subRuns.map((subRun) => {
                const renderButtons = () => {
                  switch (subRun.status) {
                    case 'success':
                      return (
                        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors">
                          View
                        </button>
                      );
                    case 'failure':
                      return (
                        <>
                          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors">
                            View
                          </button>
                          <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors">
                            Reprocess
                          </button>
                          <button className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium transition-colors">
                            Skip
                          </button>
                        </>
                      );
                    case 'needs_template':
                      return (
                        <>
                          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors">
                            Build Template
                          </button>
                          <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors">
                            Reprocess
                          </button>
                          <button className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium transition-colors">
                            Skip
                          </button>
                        </>
                      );
                    case 'skipped':
                      return (
                        <>
                          <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors">
                            Reprocess
                          </button>
                          <button className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium transition-colors">
                            Delete
                          </button>
                        </>
                      );
                    case 'processing':
                    case 'not_started':
                    default:
                      return null;
                  }
                };

                return (
                  <div
                    key={subRun.id}
                    className="bg-gray-700/30 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getStatusColor(subRun.status)}`}>
                          {getStatusIcon(subRun.status)}
                        </span>
                        <div>
                          <h3 className="text-white font-semibold">
                            Pages {subRun.pageStart}-{subRun.pageEnd}
                            {subRun.template && ` • ${subRun.template.name}`}
                          </h3>
                          {subRun.template && (
                            <p className="text-gray-400 text-sm">{subRun.template.description}</p>
                          )}
                          {subRun.status === 'needs_template' && (
                            <p className="text-yellow-400 text-sm">No matching template found</p>
                          )}
                        </div>
                      </div>

                      <div className="flex gap-2">
                        {renderButtons()}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Sidebar - 1 column */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Actions</h2>
            <div className="space-y-2">
              <button className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-semibold transition-colors">
                View PDF
              </button>
              {(() => {
                const hasNonSuccessRuns = mockEtoRunDetail.subRuns.some(sr => sr.status !== 'success');
                return (
                  <>
                    <button
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
                      disabled={!hasNonSuccessRuns}
                      className={`w-full px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        hasNonSuccessRuns
                          ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                          : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                      }`}
                    >
                      Skip All
                    </button>
                  </>
                );
              })()}
              <button className="w-full px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-md text-sm transition-colors">
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
                <p className="text-white">{mockEtoRunDetail.pdfFile.fileSize}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Total Pages</p>
                <p className="text-white">{mockEtoRunDetail.totalPages}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Received</p>
                <p className="text-white">{mockEtoRunDetail.sourceDate}</p>
              </div>
            </div>
          </div>

          {/* Page Breakdown */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Page Breakdown</h2>
            <div className="flex flex-wrap gap-2">
              {Array.from({ length: mockEtoRunDetail.totalPages }, (_, i) => {
                const pageNum = i + 1;
                const subRun = mockEtoRunDetail.subRuns.find(
                  sr => pageNum >= sr.pageStart && pageNum <= sr.pageEnd
                );
                const statusColor = subRun ? getStatusColor(subRun.status) : 'text-gray-500 bg-gray-500/10';

                return (
                  <div
                    key={pageNum}
                    className={`w-10 h-10 flex items-center justify-center rounded text-sm font-semibold ${statusColor}`}
                    title={subRun?.template?.name || 'No template'}
                  >
                    {pageNum}
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex flex-wrap gap-3 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-green-400/10"></div>
                <span className="text-gray-400">Processed</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-yellow-400/10"></div>
                <span className="text-gray-400">Needs Template</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
