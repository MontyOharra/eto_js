import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  EtoPageHeader,
  EtoRunsTable,
  EtoRunDetailViewWrapper,
  useEtoRuns,
  useUploadAndCreateEtoRun,
  useReprocessRun,
  useSkipRun,
  useDeleteRuns,
  useUpdateEtoRun,
  useEtoEvents,
  EtoSubRunStatus,
  SortOption,
} from '../../../features/eto';
import { PdfViewerModal } from '../../../features/pdf';

export const Route = createFileRoute('/dashboard/eto/')({
  component: EtoPage,
});

/**
 * Custom hook for debouncing a value
 */
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

function EtoPage() {

  // Detail view state - when set, shows detail view instead of list
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // SSE connection for real-time updates
  // Disable fallback polling when viewing detail view (list is hidden anyway)
  const [isLiveConnected, setIsLiveConnected] = useState(false);
  useEtoEvents({
    onConnected: () => setIsLiveConnected(true),
    onDisconnected: () => setIsLiveConnected(false),
    fallbackPollingInterval: selectedRunId !== null ? 0 : undefined,
  });

  // Filter state - immediate values for controlled inputs
  const [searchQuery, setSearchQuery] = useState('');
  const [subRunStatusFilter, setSubRunStatusFilter] = useState<EtoSubRunStatus | 'all'>('all');
  const [readFilter, setReadFilter] = useState<'all' | 'read' | 'unread'>('all');
  const [sortOption, setSortOption] = useState<SortOption>('last_processed_at-desc');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  // Debounce search query to avoid excessive API calls while typing
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // Parse sort option into sort_by and sort_order
  const [sortBy, sortOrder] = sortOption.split('-') as [string, 'asc' | 'desc'];

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedSearchQuery, subRunStatusFilter, readFilter, sortOption]);

  // PDF Viewer modal state
  const [viewingPdfId, setViewingPdfId] = useState<number | null>(null);
  const [viewingPdfFilename, setViewingPdfFilename] = useState<string | undefined>(undefined);

  // Upload progress state
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number } | null>(null);

  // Build query params from filter state (use debounced search)
  const queryParams = {
    search: debouncedSearchQuery || undefined,
    has_sub_run_status: subRunStatusFilter !== 'all' ? subRunStatusFilter : undefined,
    is_read: readFilter === 'read' ? true : readFilter === 'unread' ? false : undefined,
    sort_by: sortBy as any,
    sort_order: sortOrder,
    limit: itemsPerPage,
    offset: (currentPage - 1) * itemsPerPage,
  };

  // Fetch ETO runs from API
  // isLoading = true only on first load (no cached data)
  // isFetching = true during any fetch (including refetches)
  const { data, isLoading, isFetching, isError, error } = useEtoRuns(queryParams);

  // Mutation for uploading PDF and creating ETO run
  const uploadAndCreateRun = useUploadAndCreateEtoRun();

  // Run-level mutations
  const reprocessRun = useReprocessRun();
  const skipRun = useSkipRun();
  const deleteRuns = useDeleteRuns();
  const updateRun = useUpdateEtoRun();

  // Row action handlers
  const handleReprocess = (runId: number) => {
    reprocessRun.mutate(runId);
  };

  const handleSkip = (runId: number) => {
    skipRun.mutate(runId);
  };

  const handleDelete = (runId: number) => {
    if (confirm('Are you sure you want to delete this run? This action cannot be undone.')) {
      deleteRuns.mutate({ run_ids: [runId] });
    }
  };

  const handleViewPdf = (pdfId: number, filename?: string) => {
    setViewingPdfId(pdfId);
    setViewingPdfFilename(filename);
  };

  const handleClosePdfViewer = () => {
    setViewingPdfId(null);
    setViewingPdfFilename(undefined);
  };

  const handleToggleRead = (runId: number, isRead: boolean) => {
    updateRun.mutate({ runId, updates: { is_read: isRead } });
  };

  const handleRowClick = (runId: number) => {
    setSelectedRunId(runId);
  };

  const handleBackToList = () => {
    setSelectedRunId(null);
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setSubRunStatusFilter('all');
    setReadFilter('all');
    setSortOption('last_processed_at-desc');
  };

  const handleUploadPdf = () => {
    // Create a hidden file input element
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/pdf';
    input.multiple = true; // Allow multiple file selection

    input.onchange = async (e: Event) => {
      const target = e.target as HTMLInputElement;
      const files = Array.from(target.files || []);

      if (files.length === 0) return;

      // Validate all files are PDFs
      const invalidFiles = files.filter(f => f.type !== 'application/pdf');
      if (invalidFiles.length > 0) {
        alert(
          invalidFiles.length === 1
            ? `"${invalidFiles[0].name}" is not a PDF file`
            : `${invalidFiles.length} files are not PDFs. Please select only PDF files.`
        );
        return;
      }

      // Upload all files sequentially with progress tracking
      const totalFiles = files.length;
      let successCount = 0;
      let failedFiles: string[] = [];

      try {
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          setUploadProgress({ current: i + 1, total: totalFiles });

          try {
            await uploadAndCreateRun.mutateAsync(file);
            successCount++;
          } catch (err) {
            console.error(`Failed to upload ${file.name}:`, err);
            failedFiles.push(file.name);
          }
        }
      } finally {
        // Clear progress when done
        setUploadProgress(null);

        // Show summary if there were failures
        if (failedFiles.length > 0) {
          alert(
            `Upload complete:\n` +
            `✓ ${successCount} succeeded\n` +
            `✗ ${failedFiles.length} failed\n\n` +
            `Failed files:\n${failedFiles.join('\n')}`
          );
        }
      }
    };

    // Trigger the file picker
    input.click();
  };

  // Only show full-page loading on initial load (no cached data yet)
  if (isLoading && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-400">Loading ETO runs...</div>
      </div>
    );
  }

  // Error state - only show if we have no data to display
  if (isError && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-red-400">Error loading ETO runs: {error?.message || 'Unknown error'}</div>
      </div>
    );
  }

  const items = data?.items || [];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Detail view - shown when a run is selected */}
      {selectedRunId && (
        <EtoRunDetailViewWrapper
          runId={selectedRunId}
          onBack={handleBackToList}
        />
      )}

      {/* List view - kept mounted but hidden when detail view is open to preserve scroll position */}
      <div className={`h-full flex flex-col overflow-hidden ${selectedRunId ? 'hidden' : ''}`}>
        {/* Header Section */}
        <EtoPageHeader
            title="ETO Runs"
            subtitle="Email-to-Output Processing Dashboard"
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
            subRunStatusFilter={subRunStatusFilter}
            onSubRunStatusFilterChange={setSubRunStatusFilter}
            readFilter={readFilter}
            onReadFilterChange={setReadFilter}
            sortOption={sortOption}
            onSortOptionChange={setSortOption}
            onClearFilters={handleClearFilters}
          />

          {/* Action Bar */}
          <div className="px-6 pb-4 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-4">
              {/* Gmail-style Pagination */}
              <div className="text-sm text-gray-400 flex items-center gap-3">
                <span>
                  {data?.total === 0 ? '0' : `${(currentPage - 1) * itemsPerPage + 1}-${Math.min(currentPage * itemsPerPage, data?.total ?? 0)}`} of {data?.total ?? 0}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setCurrentPage(p => p - 1)}
                    disabled={currentPage === 1}
                    className="p-1.5 rounded hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    title="Previous page"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => setCurrentPage(p => p + 1)}
                    disabled={currentPage * itemsPerPage >= (data?.total ?? 0)}
                    className="p-1.5 rounded hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    title="Next page"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
                {/* Subtle loading indicator during refetches */}
                {isFetching && (
                  <span className="inline-block w-4 h-4 border-2 border-gray-600 border-t-blue-500 rounded-full animate-spin" />
                )}
              </div>
            </div>
            <button
              onClick={handleUploadPdf}
              disabled={uploadAndCreateRun.isPending || uploadProgress !== null}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploadProgress
                ? `Uploading ${uploadProgress.current}/${uploadProgress.total}...`
                : uploadAndCreateRun.isPending
                ? 'Uploading...'
                : '+ Upload PDF'}
            </button>
          </div>

          {/* Scrollable Table Container */}
          <div className="flex-1 min-h-0 px-6 pb-6">
            <EtoRunsTable
              data={items}
              onRowClick={handleRowClick}
              onReprocess={handleReprocess}
              onSkip={handleSkip}
              onDelete={handleDelete}
              onViewPdf={handleViewPdf}
              onToggleRead={handleToggleRead}
            />
          </div>
        </div>

      {/* PDF Viewer Modal - shown in both views */}
      <PdfViewerModal
        isOpen={viewingPdfId !== null}
        pdfId={viewingPdfId}
        filename={viewingPdfFilename}
        onClose={handleClosePdfViewer}
      />
    </div>
  );
}
