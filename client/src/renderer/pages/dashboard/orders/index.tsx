import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  UnifiedActionsTable,
  PendingOrderDetailView,
  PendingUpdateDetailView,
  OrderHistoryTimeline,
  usePendingOrderDetail,
  useConfirmField,
  useApprovePendingOrder,
  useRejectPendingOrder,
  usePendingUpdateDetail,
  useOrderHistory,
  useApprovePendingUpdate,
  useRejectPendingUpdate,
  useConfirmUpdateField,
  useUnifiedActions,
  useMarkRead,
  ActionType,
} from '../../../features/order-management';
import { useOrderEvents } from '../../../features/order-management/hooks';
import { useCustomers } from '../../../features/templates/api/hooks';
import { EtoSubRunDetailViewer } from '../../../features/eto';
import { useAuth } from '../../../contexts/AuthContext';

export const Route = createFileRoute('/dashboard/orders/')({
  component: OrdersPage,
});

type DetailView =
  | { type: 'order-detail'; orderId: number }
  | { type: 'update-detail'; updateId: number }
  | { type: 'order-history'; hawb: string }
  | null;

// Filter types
type TypeFilter = 'all' | 'create' | 'update';
type StatusFilter = 'all' | string;

// Status options for each type
const CREATE_STATUSES = [
  { value: 'incomplete', label: 'Incomplete' },
  { value: 'ready', label: 'Ready' },
  { value: 'processing', label: 'Processing' },
  { value: 'created', label: 'Created' },
  { value: 'failed', label: 'Failed' },
];

const UPDATE_STATUSES = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
];

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

function OrdersPage() {
  // Connect to SSE for real-time updates
  useOrderEvents();

  // Fetch customers for dropdown
  const { data: customers, isLoading: customersLoading } = useCustomers();

  // Get current user from auth context
  const { session } = useAuth();

  // Detail view state
  const [detailView, setDetailView] = useState<DetailView>(null);

  // ETO Sub-run viewer modal state
  const [viewingSubRunId, setViewingSubRunId] = useState<number | null>(null);

  // ============================================================================
  // Filter State
  // ============================================================================
  const [customerFilter, setCustomerFilter] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [page, setPage] = useState(1);
  const perPage = 20;

  // Debounce search query for real-time feedback (300ms delay)
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // Reset page when filters change (use debounced search)
  useEffect(() => {
    setPage(1);
  }, [customerFilter, debouncedSearchQuery, typeFilter, statusFilter]);

  // Build query params for the API
  const unifiedQueryParams = {
    type: typeFilter !== 'all' ? (typeFilter as ActionType) : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    customer_id: customerFilter ?? undefined,
    search: debouncedSearchQuery || undefined,
    limit: perPage,
    offset: (page - 1) * perPage,
  };

  const {
    data: unifiedData,
    isLoading: unifiedLoading,
    isFetching: unifiedFetching,
  } = useUnifiedActions(unifiedQueryParams);

  // Detail data - Pending Orders
  const selectedOrderId =
    detailView?.type === 'order-detail' ? detailView.orderId : null;
  const { data: orderDetail } = usePendingOrderDetail(selectedOrderId);

  const selectedHawb =
    detailView?.type === 'order-history' ? detailView.hawb : null;
  const { data: orderHistory } = useOrderHistory(selectedHawb);

  // Detail data - Pending Updates
  const selectedUpdateId =
    detailView?.type === 'update-detail' ? detailView.updateId : null;
  const { data: updateDetail } = usePendingUpdateDetail(selectedUpdateId);

  // Mutations - Pending Orders
  const confirmField = useConfirmField();
  const approvePendingOrder = useApprovePendingOrder();
  const rejectPendingOrder = useRejectPendingOrder();

  // Mutations - Pending Updates
  const approveUpdate = useApprovePendingUpdate();
  const rejectUpdate = useRejectPendingUpdate();
  const confirmUpdateField = useConfirmUpdateField();
  const markRead = useMarkRead();

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleClearFilters = () => {
    setCustomerFilter(null);
    setSearchQuery('');
    setTypeFilter('all');
    setStatusFilter('all');
  };

  const handleRowClick = (type: ActionType, id: number) => {
    // Mark as read when clicking into detail
    markRead.mutate({ type, id, is_read: true });

    if (type === 'create') {
      setDetailView({ type: 'order-detail', orderId: id });
    } else {
      setDetailView({ type: 'update-detail', updateId: id });
    }
  };

  const handleToggleRead = (type: ActionType, id: number, isRead: boolean) => {
    markRead.mutate({ type, id, is_read: isRead });
  };

  const handleApproveUpdate = (updateId: number) => {
    // Get the current user's username for audit trail
    const approverUsername = session?.user?.username || 'ETO_SYSTEM';
    approveUpdate.mutate({ updateId, approverUsername });
  };

  const handleRejectUpdate = (updateId: number) => {
    rejectUpdate.mutate({ updateId });
  };

  // Track which update fields are currently being confirmed
  const [confirmingUpdateFields, setConfirmingUpdateFields] = useState<Set<string>>(new Set());

  const handleConfirmUpdateField = (fieldName: string, historyId: number) => {
    if (!selectedUpdateId) return;

    setConfirmingUpdateFields((prev) => new Set(prev).add(fieldName));

    confirmUpdateField.mutate(
      {
        pendingUpdateId: selectedUpdateId,
        fieldName,
        historyId,
      },
      {
        onSettled: () => {
          setConfirmingUpdateFields((prev) => {
            const next = new Set(prev);
            next.delete(fieldName);
            return next;
          });
        },
      }
    );
  };

  const handleBackToList = () => {
    setDetailView(null);
  };

  const handleApprovePendingOrder = () => {
    if (!selectedOrderId) return;
    const approverUsername = session?.user?.username || 'ETO_SYSTEM';
    approvePendingOrder.mutate(
      { pendingOrderId: selectedOrderId, approverUsername },
      {
        onSuccess: () => {
          // Go back to list after successful creation
          setDetailView(null);
        },
      }
    );
  };

  const handleRejectPendingOrder = () => {
    if (!selectedOrderId) return;
    rejectPendingOrder.mutate(
      { pendingOrderId: selectedOrderId },
      {
        onSuccess: () => {
          // Go back to list after successful rejection
          setDetailView(null);
        },
      }
    );
  };

  const handleViewSubRun = (subRunId: number) => {
    setViewingSubRunId(subRunId);
  };

  const handleCloseSubRunViewer = () => {
    setViewingSubRunId(null);
  };

  // Track which fields are currently being confirmed
  const [confirmingFields, setConfirmingFields] = useState<Set<string>>(new Set());

  const handleConfirmField = (fieldName: string, historyId: number) => {
    if (!selectedOrderId) return;

    // Add field to confirming set
    setConfirmingFields((prev) => new Set(prev).add(fieldName));

    confirmField.mutate(
      {
        pendingOrderId: selectedOrderId,
        fieldName,
        historyId,
      },
      {
        onSettled: () => {
          // Remove field from confirming set when done
          setConfirmingFields((prev) => {
            const next = new Set(prev);
            next.delete(fieldName);
            return next;
          });
        },
      }
    );
  };

  // ============================================================================
  // Render Detail Views
  // ============================================================================

  if (detailView?.type === 'order-detail' && orderDetail) {
    return (
      <>
        <PendingOrderDetailView
          order={orderDetail}
          onBack={handleBackToList}
          onConfirmField={handleConfirmField}
          onViewSubRun={handleViewSubRun}
          confirmingFields={confirmingFields}
          onApprove={handleApprovePendingOrder}
          onReject={handleRejectPendingOrder}
          isApproving={approvePendingOrder.isPending}
          isRejecting={rejectPendingOrder.isPending}
        />
        <EtoSubRunDetailViewer
          isOpen={viewingSubRunId !== null}
          subRunId={viewingSubRunId}
          onClose={handleCloseSubRunViewer}
        />
      </>
    );
  }

  if (detailView?.type === 'order-history' && orderHistory) {
    return (
      <>
        <OrderHistoryTimeline
          history={orderHistory}
          onBack={handleBackToList}
          onViewSubRun={handleViewSubRun}
        />
        <EtoSubRunDetailViewer
          isOpen={viewingSubRunId !== null}
          subRunId={viewingSubRunId}
          onClose={handleCloseSubRunViewer}
        />
      </>
    );
  }

  if (detailView?.type === 'update-detail' && updateDetail) {
    return (
      <>
        <PendingUpdateDetailView
          update={updateDetail}
          onBack={handleBackToList}
          onApprove={handleApproveUpdate}
          onReject={handleRejectUpdate}
          onConfirmField={handleConfirmUpdateField}
          onViewSubRun={handleViewSubRun}
          isApproving={approveUpdate.isPending}
          isRejecting={rejectUpdate.isPending}
          confirmingFields={confirmingUpdateFields}
        />
        <EtoSubRunDetailViewer
          isOpen={viewingSubRunId !== null}
          subRunId={viewingSubRunId}
          onClose={handleCloseSubRunViewer}
        />
      </>
    );
  }

  // ============================================================================
  // Render Main View
  // ============================================================================

  // Get available status options based on type filter
  const getStatusOptions = () => {
    if (typeFilter === 'create') {
      return CREATE_STATUSES;
    } else if (typeFilter === 'update') {
      return UPDATE_STATUSES;
    }
    // All types - combine both (will show all statuses)
    return [...CREATE_STATUSES, ...UPDATE_STATUSES];
  };

  const hasActiveFilters =
    customerFilter !== null ||
    searchQuery !== '' ||
    typeFilter !== 'all' ||
    statusFilter !== 'all';

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 flex-shrink-0 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Pending Actions</h2>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="text-sm text-gray-400 hover:text-white transition-colors flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Clear filters
            </button>
          )}
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-3">
          {/* Customer Dropdown */}
          <div className="relative">
            <select
              value={customerFilter ?? ''}
              onChange={(e) => setCustomerFilter(e.target.value ? Number(e.target.value) : null)}
              disabled={customersLoading}
              className="appearance-none bg-gray-700 border border-gray-600 rounded-lg pl-3 pr-8 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[180px] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">
                {customersLoading ? 'Loading...' : 'All Customers'}
              </option>
              {customers?.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>

          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by HAWB or Order #..."
              className="w-full bg-gray-700 border border-gray-600 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-white"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Spacer */}
          <div className="flex-shrink-0 w-px h-8 bg-gray-600" />

          {/* Type Filter */}
          <div className="relative">
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value as TypeFilter);
                setStatusFilter('all'); // Reset status when type changes
              }}
              className="appearance-none bg-gray-700 border border-gray-600 rounded-lg pl-3 pr-8 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[130px]"
            >
              <option value="all">All Types</option>
              <option value="create">Creates</option>
              <option value="update">Updates</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>

          {/* Status Filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="appearance-none bg-gray-700 border border-gray-600 rounded-lg pl-3 pr-8 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[140px]"
            >
              <option value="all">All Statuses</option>
              {getStatusOptions().map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Pagination */}
      <div className="px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="text-sm text-gray-400 flex items-center gap-3">
          <span>
            {unifiedData?.total === 0
              ? '0'
              : `${(page - 1) * perPage + 1}-${Math.min(
                  page * perPage,
                  unifiedData?.total ?? 0
                )}`}{' '}
            of {unifiedData?.total ?? 0}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 1}
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
              onClick={() => setPage((p) => p + 1)}
              disabled={page * perPage >= (unifiedData?.total ?? 0)}
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
          {unifiedFetching && (
            <span className="inline-block w-4 h-4 border-2 border-gray-600 border-t-blue-500 rounded-full animate-spin" />
          )}
        </div>
      </div>

      {/* Unified Table */}
      <div className="flex-1 min-h-0 px-6 pb-6">
        {unifiedLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-gray-400">Loading pending actions...</div>
          </div>
        ) : (
          <UnifiedActionsTable
            data={unifiedData?.items ?? []}
            onRowClick={handleRowClick}
            onToggleRead={handleToggleRead}
          />
        )}
      </div>

      {/* ETO Sub-run Detail Modal */}
      <EtoSubRunDetailViewer
        isOpen={viewingSubRunId !== null}
        subRunId={viewingSubRunId}
        onClose={handleCloseSubRunViewer}
      />
    </div>
  );
}
