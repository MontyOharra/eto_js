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
  masterStatus: 'failure',
  totalPages: 15,
  createdAt: '2024-01-15 10:45:32',
  lastUpdated: '2024-01-15 11:02:14',
  processingStep: 'sub_runs',

  // PDF file info
  pdfFile: {
    id: 123,
    storagePath: '/storage/uploads/receipts_jan_2024.pdf',
    fileSize: '3.8 MB',
  },

  // Email details (if from email)
  emailDetails: null,

  // Matched sub-runs (with template matches)
  matchedSubRuns: [
    {
      id: 1,
      pages: [1, 2, 3],
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
        poNumber: 'PO-9876',
      },
      processedAt: '2024-01-15 10:52:08',
      errorMessage: null,
    },
    {
      id: 2,
      pages: [4, 5],
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
        poNumber: 'PO-9877',
      },
      processedAt: '2024-01-15 10:58:22',
      errorMessage: null,
    },
    {
      id: 3,
      pages: [8, 9],
      status: 'failure',
      template: {
        id: 7,
        name: 'Shipping Invoice Template',
        description: 'UPS/FedEx shipping invoice format',
      },
      extractedData: null,
      processedAt: '2024-01-15 11:01:45',
      errorMessage: 'Failed to extract tracking number: OCR confidence too low (0.42)',
    },
    {
      id: 4,
      pages: [12],
      status: 'failure',
      template: {
        id: 5,
        name: 'Vendor Receipt Template',
        description: 'Standard vendor receipt format',
      },
      extractedData: null,
      processedAt: '2024-01-15 11:02:10',
      errorMessage: 'Missing required field: total amount not found in expected region',
    },
  ],

  // Needs template sub-runs (no template match found)
  needsTemplateSubRuns: [
    {
      id: 5,
      pages: [6, 7],
      status: 'needs_template',
      createdAt: '2024-01-15 10:47:22',
    },
    {
      id: 6,
      pages: [13],
      status: 'needs_template',
      createdAt: '2024-01-15 10:47:22',
    },
  ],

  // Skipped sub-runs (user explicitly skipped)
  skippedSubRuns: [
    {
      id: 7,
      pages: [10, 11, 14, 15],
      status: 'skipped',
      skippedAt: '2024-01-15 11:05:18',
      skippedReason: 'Consolidated from failed extraction attempts',
    },
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
                <p className="text-white text-lg font-semibold mt-1">{mockEtoRunDetail.matchedSubRuns.length}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Processing Time</p>
                <p className="text-white text-lg font-semibold mt-1">16m 42s</p>
              </div>
            </div>
          </div>

          {/* Sub-runs Section - Matched Templates */}
          {mockEtoRunDetail.matchedSubRuns.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">Matched Templates ({mockEtoRunDetail.matchedSubRuns.length})</h2>
                <span className="text-gray-400 text-sm">
                  {mockEtoRunDetail.matchedSubRuns.filter(sr => sr.status === 'success').length} successful, {mockEtoRunDetail.matchedSubRuns.filter(sr => sr.status === 'failure').length} failed
                </span>
              </div>

              <div className="space-y-3">
                {mockEtoRunDetail.matchedSubRuns.map((subRun) => (
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
                          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap">
                            View Details
                          </button>
                        )}
                        {subRun.status === 'failure' && (
                          <>
                            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap">
                              View Details
                            </button>
                            <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap">
                              Reprocess
                            </button>
                            <button className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap">
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
                            <span className="text-gray-300">{value as string}</span>
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
          )}

          {/* Needs Template Section */}
          {mockEtoRunDetail.needsTemplateSubRuns.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">Needs Template ({mockEtoRunDetail.needsTemplateSubRuns.length})</h2>
                <span className="text-yellow-400 text-sm">
                  {mockEtoRunDetail.needsTemplateSubRuns.reduce((acc, sr) => acc + sr.pages.length, 0)} pages unmatched
                </span>
              </div>

              <div className="space-y-3">
                {mockEtoRunDetail.needsTemplateSubRuns.map((subRun) => (
                  <div
                    key={subRun.id}
                    className="bg-yellow-900/10 rounded-lg p-4 border border-yellow-700/50 hover:border-yellow-600 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getStatusColor('needs_template')}`}>
                          {getStatusIcon('needs_template')}
                        </span>
                        <div>
                          <h3 className="text-white font-semibold">
                            Pages {subRun.pages.join(', ')}
                          </h3>
                          <p className="text-yellow-400 text-sm">No matching template found</p>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap">
                          Build Template
                        </button>
                        <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap">
                          Reprocess
                        </button>
                        <button className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap">
                          Skip
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Skipped Section */}
          {mockEtoRunDetail.skippedSubRuns.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">Skipped ({mockEtoRunDetail.skippedSubRuns.length})</h2>
                <span className="text-gray-400 text-sm">
                  {mockEtoRunDetail.skippedSubRuns.reduce((acc, sr) => acc + sr.pages.length, 0)} pages skipped
                </span>
              </div>

              <div className="space-y-3">
                {mockEtoRunDetail.skippedSubRuns.map((subRun) => (
                  <div
                    key={subRun.id}
                    className="bg-gray-700/50 rounded-lg p-4 border border-gray-600 hover:border-gray-500 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-gray-400 bg-gray-400/10`}>
                          ⊘
                        </span>
                        <div>
                          <h3 className="text-white font-semibold">
                            Pages {subRun.pages.join(', ')}
                          </h3>
                          <p className="text-gray-400 text-sm">{subRun.skippedReason}</p>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap">
                          Reprocess
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
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
                const hasFailedRuns = mockEtoRunDetail.matchedSubRuns.some(sr => sr.status === 'failure');
                const hasNeedsTemplate = mockEtoRunDetail.needsTemplateSubRuns.length > 0;
                const hasNonSuccessRuns = hasFailedRuns || hasNeedsTemplate;

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

                // Check all sub-run types for this page
                const matchedSubRun = mockEtoRunDetail.matchedSubRuns.find(sr => sr.pages.includes(pageNum));
                const needsTemplateSubRun = mockEtoRunDetail.needsTemplateSubRuns.find(sr => sr.pages.includes(pageNum));
                const skippedSubRun = mockEtoRunDetail.skippedSubRuns.find(sr => sr.pages.includes(pageNum));

                const subRun = matchedSubRun || needsTemplateSubRun || skippedSubRun;
                const status = matchedSubRun?.status || needsTemplateSubRun?.status || skippedSubRun?.status;
                const statusColor = status ? getStatusColor(status) : 'text-gray-500 bg-gray-500/10';
                const tooltipText = matchedSubRun?.template?.name || (needsTemplateSubRun ? 'No template' : (skippedSubRun ? 'Skipped' : 'Unprocessed'));

                return (
                  <div
                    key={pageNum}
                    className={`w-10 h-10 flex items-center justify-center rounded text-sm font-semibold ${statusColor}`}
                    title={tooltipText}
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
      </div>
    </div>
  );
}
