import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import {
  Table,
  EtoRunRow,
  TestPageHeader,
  useEtoRuns,
  useUploadAndCreateEtoRun,
  EtoRunStatus,
} from '../../../features/test';

export const Route = createFileRoute('/dashboard/test/')({
  component: TestPage,
});

function TestPage() {
  const navigate = useNavigate();

  // Filter state
  const [searchScope, setSearchScope] = useState('filename');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | EtoRunStatus>('all');
  const [readFilter, setReadFilter] = useState<'all' | 'read' | 'unread'>('all');

  // Build query params from filter state
  const queryParams = {
    status: statusFilter !== 'all' ? statusFilter : undefined,
    is_read: readFilter === 'read' ? true : readFilter === 'unread' ? false : undefined,
    sort_by: 'updated_at' as const,
    sort_order: 'desc' as const,
    limit: 50,
    offset: 0,
  };

  // Fetch ETO runs from API
  const { data, isLoading, isError, error } = useEtoRuns(queryParams);

  // Mutation for uploading PDF and creating ETO run
  const uploadAndCreateRun = useUploadAndCreateEtoRun();

  const handleRowClick = (runId: number) => {
    navigate({ to: '/dashboard/test/$runId', params: { runId: runId.toString() } });
  };

  const handleClearFilters = () => {
    setSearchScope('filename');
    setSearchQuery('');
    setStatusFilter('all');
    setReadFilter('all');
  };

  const handleUploadPdf = () => {
    // Create a hidden file input element
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/pdf';

    input.onchange = async (e: Event) => {
      const target = e.target as HTMLInputElement;
      const file = target.files?.[0];

      if (file) {
        // Validate file type
        if (file.type !== 'application/pdf') {
          alert('Please select a PDF file');
          return;
        }

        try {
          // Upload PDF and create ETO run
          await uploadAndCreateRun.mutateAsync(file);
        } catch (err) {
          console.error('Failed to upload PDF:', err);
          alert('Failed to upload PDF. Please try again.');
        }
      }
    };

    // Trigger the file picker
    input.click();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-400">Loading ETO runs...</div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-red-400">Error loading ETO runs: {error?.message || 'Unknown error'}</div>
      </div>
    );
  }

  const items = data?.items || [];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header Section */}
      <TestPageHeader
        title="Test Page"
        subtitle="New ETO dashboard prototyping area"
        searchScope={searchScope}
        onSearchScopeChange={setSearchScope}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        readFilter={readFilter}
        onReadFilterChange={setReadFilter}
        onDateRangeClick={() => {/* TODO: Implement date range picker */}}
        onClearFilters={handleClearFilters}
      />

      {/* Action Bar */}
      <div className="px-6 pb-4 flex items-center justify-between flex-shrink-0">
        <div className="text-sm text-gray-400">
          {data?.total ?? 0} total runs
        </div>
        <button
          onClick={handleUploadPdf}
          disabled={uploadAndCreateRun.isPending}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploadAndCreateRun.isPending ? 'Uploading...' : '+ Upload PDF'}
        </button>
      </div>

      {/* Scrollable Table Container */}
      <div className="flex-1 min-h-0 px-6 pb-6">
        <Table>
          <Table.Header>
            <div className="px-6">
              <div className="grid gap-4" style={{ gridTemplateColumns: '2fr 2fr 1fr 100px 1fr auto 400px' }}>
                {/* PDF Filename header - needs to account for 32px indicator space + 8px gap */}
                <div className="flex items-center gap-2">
                  <div className="w-8 flex-shrink-0"></div>
                  <span className="text-gray-400 font-semibold text-sm uppercase break-words">PDF Filename</span>
                </div>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Source</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Received</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Status</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Pages</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Last Updated</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words text-right">Actions</span>
              </div>
            </div>
          </Table.Header>

          <Table.Body>
            {items.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-400">
                No ETO runs found
              </div>
            ) : (
              items.map((item, index) => (
                <div key={item.id}>
                  <EtoRunRow data={item} onClick={() => handleRowClick(item.id)} />
                  {index < items.length - 1 && (
                    <div className="mx-6 border-b border-gray-700" />
                  )}
                </div>
              ))
            )}
          </Table.Body>
        </Table>
      </div>
    </div>
  );
}
