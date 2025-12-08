import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  PendingOrdersHeader,
  PendingOrdersTable,
  PendingOrderDetail,
  PendingUpdatesHeader,
  PendingUpdatesTable,
  OrderHistoryTimeline,
  usePendingOrders,
  usePendingOrderDetail,
  usePendingUpdatesGrouped,
  useOrderHistory,
  useApprovePendingUpdate,
  useRejectPendingUpdate,
  useBulkApprovePendingUpdates,
  useBulkRejectPendingUpdates,
  PendingOrderSortOption,
  PendingUpdateSortOption,
  PendingOrderStatus,
} from '../../../features/order-management';

export const Route = createFileRoute('/dashboard/orders/')({
  component: OrdersPage,
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

type ViewMode = 'pending-orders' | 'pending-updates';
type DetailView =
  | { type: 'order-detail'; orderId: number }
  | { type: 'order-history'; hawb: string }
  | null;

function OrdersPage() {
  // View mode toggle
  const [viewMode, setViewMode] = useState<ViewMode>('pending-orders');

  // Detail view state
  const [detailView, setDetailView] = useState<DetailView>(null);

  // ============================================================================
  // Pending Orders State
  // ============================================================================
  const [ordersSearchQuery, setOrdersSearchQuery] = useState('');
  const [ordersStatusFilter, setOrdersStatusFilter] = useState<
    PendingOrderStatus | 'all'
  >('all');
  const [ordersSortOption, setOrdersSortOption] =
    useState<PendingOrderSortOption>('updated_at-desc');
  const [ordersPage, setOrdersPage] = useState(1);
  const ordersPerPage = 20;

  const debouncedOrdersSearch = useDebounce(ordersSearchQuery, 300);

  // Reset page when filters change
  useEffect(() => {
    setOrdersPage(1);
  }, [debouncedOrdersSearch, ordersStatusFilter, ordersSortOption]);

  const [ordersSortBy, ordersSortOrder] = ordersSortOption.split('-') as [
    string,
    'asc' | 'desc'
  ];

  const ordersQueryParams = {
    search: debouncedOrdersSearch || undefined,
    status: ordersStatusFilter !== 'all' ? ordersStatusFilter : undefined,
    sort_by: ordersSortBy,
    sort_order: ordersSortOrder,
    limit: ordersPerPage,
    offset: (ordersPage - 1) * ordersPerPage,
  };

  const {
    data: ordersData,
    isLoading: ordersLoading,
    isFetching: ordersFetching,
  } = usePendingOrders(ordersQueryParams);

  // Detail data
  const selectedOrderId =
    detailView?.type === 'order-detail' ? detailView.orderId : null;
  const { data: orderDetail } = usePendingOrderDetail(selectedOrderId);

  const selectedHawb =
    detailView?.type === 'order-history' ? detailView.hawb : null;
  const { data: orderHistory } = useOrderHistory(selectedHawb);

  // ============================================================================
  // Pending Updates State
  // ============================================================================
  const [updatesSearchQuery, setUpdatesSearchQuery] = useState('');
  const [updatesSortOption, setUpdatesSortOption] =
    useState<PendingUpdateSortOption>('proposed_at-desc');
  const [selectedUpdateIds, setSelectedUpdateIds] = useState<Set<number>>(
    new Set()
  );

  const debouncedUpdatesSearch = useDebounce(updatesSearchQuery, 300);

  const [updatesSortBy, updatesSortOrder] = updatesSortOption.split('-') as [
    string,
    'asc' | 'desc'
  ];

  const updatesQueryParams = {
    hawb: debouncedUpdatesSearch || undefined,
    sort_by: updatesSortBy,
    sort_order: updatesSortOrder,
  };

  const { data: updatesData, isLoading: updatesLoading } =
    usePendingUpdatesGrouped(updatesQueryParams);

  // Mutations
  const approveUpdate = useApprovePendingUpdate();
  const rejectUpdate = useRejectPendingUpdate();
  const bulkApprove = useBulkApprovePendingUpdates();
  const bulkReject = useBulkRejectPendingUpdates();

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleOrdersClearFilters = () => {
    setOrdersSearchQuery('');
    setOrdersStatusFilter('all');
    setOrdersSortOption('updated_at-desc');
  };

  const handleUpdatesClearFilters = () => {
    setUpdatesSearchQuery('');
    setUpdatesSortOption('proposed_at-desc');
    setSelectedUpdateIds(new Set());
  };

  const handleRowClick = (orderId: number) => {
    setDetailView({ type: 'order-detail', orderId });
  };

  const handleViewHistory = (hawb: string) => {
    setDetailView({ type: 'order-history', hawb });
  };

  const handleBackToList = () => {
    setDetailView(null);
  };

  const handleApproveUpdate = (updateId: number) => {
    approveUpdate.mutate({ updateId });
  };

  const handleRejectUpdate = (updateId: number) => {
    rejectUpdate.mutate({ updateId });
  };

  const handleBulkApprove = () => {
    if (selectedUpdateIds.size === 0) return;
    bulkApprove.mutate({ update_ids: Array.from(selectedUpdateIds) });
    setSelectedUpdateIds(new Set());
  };

  const handleBulkReject = () => {
    if (selectedUpdateIds.size === 0) return;
    bulkReject.mutate({ update_ids: Array.from(selectedUpdateIds) });
    setSelectedUpdateIds(new Set());
  };

  const handleViewRun = (runId: number) => {
    // Navigate to ETO runs page with the run selected
    // For now, just log - can implement navigation later
    console.log('View run:', runId);
  };

  // ============================================================================
  // Render Detail Views
  // ============================================================================

  if (detailView?.type === 'order-detail' && orderDetail) {
    return (
      <PendingOrderDetail
        order={orderDetail}
        onBack={handleBackToList}
        onViewHistory={handleViewHistory}
      />
    );
  }

  if (detailView?.type === 'order-history' && orderHistory) {
    return (
      <OrderHistoryTimeline
        history={orderHistory}
        onBack={handleBackToList}
        onViewRun={handleViewRun}
      />
    );
  }

  // ============================================================================
  // Render Main View
  // ============================================================================

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* View Mode Toggle */}
      <div className="px-6 pt-4 flex-shrink-0 flex items-center justify-between">
        <div className="inline-flex bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setViewMode('pending-orders')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'pending-orders'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Pending Orders
            {ordersData && ordersData.total > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-gray-700 rounded-full text-xs">
                {ordersData.total}
              </span>
            )}
          </button>
          <button
            onClick={() => setViewMode('pending-updates')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'pending-updates'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Pending Updates
            {updatesData && updatesData.total_updates > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-yellow-500/30 text-yellow-400 rounded-full text-xs">
                {updatesData.total_updates}
              </span>
            )}
          </button>
        </div>

      </div>

      {/* Pending Orders View */}
      {viewMode === 'pending-orders' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <PendingOrdersHeader
            searchQuery={ordersSearchQuery}
            onSearchQueryChange={setOrdersSearchQuery}
            statusFilter={ordersStatusFilter}
            onStatusFilterChange={setOrdersStatusFilter}
            sortOption={ordersSortOption}
            onSortOptionChange={setOrdersSortOption}
            onClearFilters={handleOrdersClearFilters}
          />

          {/* Pagination */}
          <div className="px-6 pb-4 flex items-center justify-between flex-shrink-0">
            <div className="text-sm text-gray-400 flex items-center gap-3">
              <span>
                {ordersData?.total === 0
                  ? '0'
                  : `${(ordersPage - 1) * ordersPerPage + 1}-${Math.min(
                      ordersPage * ordersPerPage,
                      ordersData?.total ?? 0
                    )}`}{' '}
                of {ordersData?.total ?? 0}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setOrdersPage((p) => p - 1)}
                  disabled={ordersPage === 1}
                  className="p-1.5 rounded hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 19l-7-7 7-7"
                    />
                  </svg>
                </button>
                <button
                  onClick={() => setOrdersPage((p) => p + 1)}
                  disabled={
                    ordersPage * ordersPerPage >= (ordersData?.total ?? 0)
                  }
                  className="p-1.5 rounded hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </button>
              </div>
              {ordersFetching && (
                <span className="inline-block w-4 h-4 border-2 border-gray-600 border-t-blue-500 rounded-full animate-spin" />
              )}
            </div>
          </div>

          {/* Table */}
          <div className="flex-1 min-h-0 px-6 pb-6">
            {ordersLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-gray-400">Loading pending orders...</div>
              </div>
            ) : (
              <PendingOrdersTable
                data={ordersData?.items ?? []}
                onRowClick={handleRowClick}
                onViewHistory={handleViewHistory}
              />
            )}
          </div>
        </div>
      )}

      {/* Pending Updates View */}
      {viewMode === 'pending-updates' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <PendingUpdatesHeader
            searchQuery={updatesSearchQuery}
            onSearchQueryChange={setUpdatesSearchQuery}
            sortOption={updatesSortOption}
            onSortOptionChange={setUpdatesSortOption}
            onClearFilters={handleUpdatesClearFilters}
            selectedCount={selectedUpdateIds.size}
            onBulkApprove={handleBulkApprove}
            onBulkReject={handleBulkReject}
          />

          {/* Table */}
          <div className="flex-1 min-h-0 px-6 pb-6 overflow-auto">
            {updatesLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-gray-400">Loading pending updates...</div>
              </div>
            ) : (
              <PendingUpdatesTable
                data={updatesData?.items ?? []}
                onApprove={handleApproveUpdate}
                onReject={handleRejectUpdate}
                onViewRun={handleViewRun}
                selectedIds={selectedUpdateIds}
                onSelectionChange={setSelectedUpdateIds}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
