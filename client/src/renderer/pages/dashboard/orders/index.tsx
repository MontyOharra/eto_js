import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  UnifiedActionsTable,
  PendingOrderDetailView,
  PendingUpdateDetailView,
  OrderHistoryTimeline,
  ReviewRequiredAlert,
  usePendingOrderDetail,
  useSelectFieldValue,
  useApprovePendingAction,
  useRejectPendingAction,
  useOrderHistory,
  useUnifiedActions,
  useMarkRead,
  useSetFieldApproval,
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
  | { type: 'action-detail'; actionId: number }
  | { type: 'order-history'; hawb: string }
  | null;

// Filter types
type TypeFilter = 'all' | 'create' | 'update';
type StatusFilter = 'all' | string;

// Status options - unified for all pending actions
const STATUS_OPTIONS = [
  { value: 'incomplete', label: 'Incomplete' },
  { value: 'conflict', label: 'Conflict' },
  { value: 'ambiguous', label: 'Ambiguous' },
  { value: 'ready', label: 'Ready' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
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

  // Navigation hook for "View in ETO" functionality
  const navigate = useNavigate();

  // Fetch customers for dropdown
  const { data: customers, isLoading: customersLoading } = useCustomers();

  // Get current user from auth context
  const { session } = useAuth();

  // Detail view state
  const [detailView, setDetailView] = useState<DetailView>(null);

  // ETO Sub-run viewer modal state
  const [viewingSubRunId, setViewingSubRunId] = useState<number | null>(null);

  // Review required alert state
  const [reviewAlert, setReviewAlert] = useState<{
    isOpen: boolean;
    actionType: 'create' | 'update';
    reviewReason: string | null;
  }>({
    isOpen: false,
    actionType: 'create',
    reviewReason: null,
  });

  // Track when user opened the detail view (for TOCTOU check on updates)
  const [detailViewedAt, setDetailViewedAt] = useState<string | null>(null);

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
    action_type: typeFilter !== 'all' ? (typeFilter as ActionType) : undefined,
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

  // Detail data - Unified action detail (works for both creates and updates)
  // The API returns action_type which we use to decide which component to render
  const selectedActionId =
    detailView?.type === 'action-detail' ? detailView.actionId : null;
  const { data: actionDetail } = usePendingOrderDetail(selectedActionId);

  const selectedHawb =
    detailView?.type === 'order-history' ? detailView.hawb : null;
  const { data: orderHistory } = useOrderHistory(selectedHawb);

  // Mutations
  const selectFieldValue = useSelectFieldValue();
  const approveAction = useApprovePendingAction();
  const rejectAction = useRejectPendingAction();
  const markRead = useMarkRead();
  const setFieldApproval = useSetFieldApproval();

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleClearFilters = () => {
    setCustomerFilter(null);
    setSearchQuery('');
    setTypeFilter('all');
    setStatusFilter('all');
  };

  const handleRowClick = (_type: ActionType, id: number) => {
    // Mark as read when clicking into detail
    markRead.mutate({ id, is_read: true });
    // Track when user opened detail view (for TOCTOU check on updates)
    setDetailViewedAt(new Date().toISOString());
    // Use unified action-detail - the API will return the actual action_type
    // which may differ from what was shown in the list (due to TOCTOU changes)
    setDetailView({ type: 'action-detail', actionId: id });
  };

  const handleToggleRead = (_type: ActionType, id: number, isRead: boolean) => {
    markRead.mutate({ id, is_read: isRead });
  };

  const handleApproveAction = (actionId: number) => {
    approveAction.mutate(
      {
        actionId,
        detailViewedAt: detailViewedAt ?? undefined,
        approverUserId: session?.user.username,
      },
      {
        onSuccess: (data) => {
          if (data.requires_review) {
            // Use action_type from API response (source of truth after TOCTOU check)
            setReviewAlert({
              isOpen: true,
              actionType: data.action_type as 'create' | 'update',
              reviewReason: data.review_reason,
            });
          }
        },
      }
    );
  };

  const handleRejectAction = (actionId: number, reason?: string) => {
    rejectAction.mutate({ actionId, reason });
  };

  // Track which update fields are currently being confirmed
  const [confirmingUpdateFields, setConfirmingUpdateFields] = useState<Set<string>>(new Set());

  // Note: historyId is actually the field_id (pending_action_fields.id)
  const handleConfirmUpdateField = (fieldName: string, fieldId: number) => {
    if (!selectedActionId) return;

    setConfirmingUpdateFields((prev) => new Set(prev).add(fieldName));

    selectFieldValue.mutate(
      {
        actionId: selectedActionId,
        fieldId,
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

  // Track which update fields are currently toggling approval
  const [togglingApprovalFields, setTogglingApprovalFields] = useState<Set<string>>(new Set());

  const handleToggleFieldApproval = (fieldName: string, isApproved: boolean) => {
    if (!selectedActionId) return;

    setTogglingApprovalFields((prev) => new Set(prev).add(fieldName));

    setFieldApproval.mutate(
      {
        actionId: selectedActionId,
        fieldName,
        isApproved,
      },
      {
        onSettled: () => {
          setTogglingApprovalFields((prev) => {
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
    setDetailViewedAt(null);
  };

  const handleApprovePendingOrder = () => {
    if (!selectedActionId || !actionDetail) return;
    approveAction.mutate(
      {
        actionId: selectedActionId,
        detailViewedAt: detailViewedAt ?? undefined,
        approverUserId: session?.user.username,
      },
      {
        onSuccess: (data) => {
          if (data.requires_review) {
            setReviewAlert({
              isOpen: true,
              actionType: actionDetail.action_type as 'create' | 'update',
              reviewReason: data.review_reason,
            });
          }
        },
      }
    );
  };

  const handleRejectPendingOrder = () => {
    if (!selectedActionId) return;
    rejectAction.mutate({ actionId: selectedActionId });
  };

  const handleViewSubRun = (subRunId: number) => {
    setViewingSubRunId(subRunId);
  };

  const handleCloseSubRunViewer = () => {
    setViewingSubRunId(null);
  };

  const handleViewInEto = (etoRunId: number) => {
    setViewingSubRunId(null); // Close the modal first
    navigate({ to: '/dashboard/eto/$runId', params: { runId: String(etoRunId) } });
  };

  const handleCloseReviewAlert = () => {
    setReviewAlert((prev) => ({ ...prev, isOpen: false }));
  };

  // Track which fields are currently being confirmed
  const [confirmingFields, setConfirmingFields] = useState<Set<string>>(new Set());

  // Note: historyId is actually the field_id (pending_action_fields.id)
  const handleConfirmField = (fieldName: string, fieldId: number) => {
    if (!selectedActionId) return;

    // Add field to confirming set
    setConfirmingFields((prev) => new Set(prev).add(fieldName));

    selectFieldValue.mutate(
      {
        actionId: selectedActionId,
        fieldId,
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

  // Unified action detail view - delegates to create or update component based on
  // the action_type returned from the API (which may have changed due to TOCTOU)
  if (detailView?.type === 'action-detail' && actionDetail) {
    // Check the action_type from the API response to decide which component to render
    if (actionDetail.action_type === 'create') {
      return (
        <>
          <PendingOrderDetailView
            order={actionDetail}
            onBack={handleBackToList}
            onConfirmField={handleConfirmField}
            onViewSubRun={handleViewSubRun}
            confirmingFields={confirmingFields}
            onApprove={handleApprovePendingOrder}
            onReject={handleRejectPendingOrder}
            isApproving={approveAction.isPending}
            isRejecting={rejectAction.isPending}
            onToggleFieldApproval={handleToggleFieldApproval}
            togglingApprovalFields={togglingApprovalFields}
          />
          <EtoSubRunDetailViewer
            isOpen={viewingSubRunId !== null}
            subRunId={viewingSubRunId}
            onClose={handleCloseSubRunViewer}
            onViewInEto={handleViewInEto}
          />
          <ReviewRequiredAlert
            isOpen={reviewAlert.isOpen}
            actionType={reviewAlert.actionType}
            reviewReason={reviewAlert.reviewReason}
            onClose={handleCloseReviewAlert}
          />
        </>
      );
    } else if (actionDetail.action_type === 'update') {
      return (
        <>
          <PendingUpdateDetailView
            update={actionDetail}
            onBack={handleBackToList}
            onApprove={(updateId: number) => handleApproveAction(updateId)}
            onReject={(updateId: number) => handleRejectAction(updateId)}
            onConfirmField={handleConfirmUpdateField}
            onToggleFieldApproval={handleToggleFieldApproval}
            onViewSubRun={handleViewSubRun}
            isApproving={approveAction.isPending}
            isRejecting={rejectAction.isPending}
            confirmingFields={confirmingUpdateFields}
            togglingApprovalFields={togglingApprovalFields}
          />
          <EtoSubRunDetailViewer
            isOpen={viewingSubRunId !== null}
            subRunId={viewingSubRunId}
            onClose={handleCloseSubRunViewer}
            onViewInEto={handleViewInEto}
          />
          <ReviewRequiredAlert
            isOpen={reviewAlert.isOpen}
            actionType={reviewAlert.actionType}
            reviewReason={reviewAlert.reviewReason}
            onClose={handleCloseReviewAlert}
          />
        </>
      );
    } else {
      // action_type === 'ambiguous' - show a placeholder for now
      // TODO: Create an AmbiguousActionView component
      return (
        <>
          <div className="h-full flex flex-col items-center justify-center text-gray-400">
            <div className="text-lg mb-2">Ambiguous Action</div>
            <div className="text-sm mb-4">
              Multiple HTC orders exist for this customer/HAWB combination.
            </div>
            <button
              onClick={handleBackToList}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white"
            >
              Back to List
            </button>
          </div>
        </>
      );
    }
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
          onViewInEto={handleViewInEto}
        />
      </>
    );
  }

  // ============================================================================
  // Render Main View
  // ============================================================================

  // Get available status options
  const getStatusOptions = () => {
    return STATUS_OPTIONS;
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
        onViewInEto={handleViewInEto}
      />

      {/* Review Required Alert */}
      <ReviewRequiredAlert
        isOpen={reviewAlert.isOpen}
        actionType={reviewAlert.actionType}
        reviewReason={reviewAlert.reviewReason}
        onClose={handleCloseReviewAlert}
      />
    </div>
  );
}
