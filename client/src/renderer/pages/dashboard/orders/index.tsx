import { createFileRoute, Link } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  UnifiedActionsTable,
  PendingOrderDetailView,
  PendingUpdateDetailView,
  OrderHistoryTimeline,
  usePendingOrderDetail,
  useConfirmField,
  usePendingUpdateDetail,
  useOrderHistory,
  useApprovePendingUpdate,
  useRejectPendingUpdate,
  useConfirmUpdateField,
  useUnifiedActions,
  useMarkRead,
  ActionType,
} from '../../../features/order-management';
import { EtoSubRunDetailViewer } from '../../../features/eto';

export const Route = createFileRoute('/dashboard/orders/')({
  component: OrdersPage,
});

type DetailView =
  | { type: 'order-detail'; orderId: number }
  | { type: 'update-detail'; updateId: number }
  | { type: 'order-history'; hawb: string }
  | null;

// Filter type for unified view
type TypeFilter = 'all' | 'create' | 'update';
type StatusFilter = 'all' | string;
type ReadFilter = 'all' | 'read' | 'unread';

function OrdersPage() {
  // Detail view state
  const [detailView, setDetailView] = useState<DetailView>(null);

  // ETO Sub-run viewer modal state
  const [viewingSubRunId, setViewingSubRunId] = useState<number | null>(null);

  // ============================================================================
  // Unified Actions State
  // ============================================================================
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [readFilter, setReadFilter] = useState<ReadFilter>('all');
  const [page, setPage] = useState(1);
  const perPage = 20;

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [typeFilter, statusFilter, readFilter]);

  const unifiedQueryParams = {
    type: typeFilter !== 'all' ? (typeFilter as ActionType) : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    is_read: readFilter === 'all' ? undefined : readFilter === 'read',
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

  // Mutations - Pending Updates
  const approveUpdate = useApprovePendingUpdate();
  const rejectUpdate = useRejectPendingUpdate();
  const confirmUpdateField = useConfirmUpdateField();
  const markRead = useMarkRead();

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleClearFilters = () => {
    setTypeFilter('all');
    setStatusFilter('all');
    setReadFilter('all');
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
    approveUpdate.mutate({ updateId });
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

  const handleViewSubRun = (subRunId: number) => {
    setViewingSubRunId(subRunId);
  };

  const handleViewHistory = (hawb: string) => {
    setDetailView({ type: 'order-history', hawb });
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
      return [
        { value: 'all', label: 'All Status' },
        { value: 'incomplete', label: 'Incomplete' },
        { value: 'ready', label: 'Ready' },
        { value: 'processing', label: 'Processing' },
        { value: 'created', label: 'Created' },
        { value: 'failed', label: 'Failed' },
      ];
    } else if (typeFilter === 'update') {
      return [
        { value: 'all', label: 'All Status' },
        { value: 'pending', label: 'Pending' },
        { value: 'approved', label: 'Approved' },
        { value: 'rejected', label: 'Rejected' },
      ];
    }
    // All types - show common subset or all
    return [
      { value: 'all', label: 'All Status' },
    ];
  };

  const hasActiveFilters = typeFilter !== 'all' || statusFilter !== 'all' || readFilter !== 'all';

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header with Filters */}
      <div className="px-6 py-4 flex-shrink-0 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-white">Pending Actions</h2>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value as TypeFilter);
              setStatusFilter('all'); // Reset status when type changes
            }}
            className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Types</option>
            <option value="create">Creates Only</option>
            <option value="update">Updates Only</option>
          </select>

          {/* Status Filter - changes based on type */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={typeFilter === 'all'}
          >
            {getStatusOptions().map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Read/Unread Filter */}
          <select
            value={readFilter}
            onChange={(e) => setReadFilter(e.target.value as ReadFilter)}
            className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Items</option>
            <option value="unread">Unread Only</option>
            <option value="read">Read Only</option>
          </select>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Preview Link */}
        <Link
          to="/dashboard/orders/layout-a"
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          Preview Detail
        </Link>
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
            onViewHistory={handleViewHistory}
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
