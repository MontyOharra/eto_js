/**
 * API request/response types for Order Management
 */

import type {
  PendingOrderListItem,
  PendingOrderDetail,
  PendingOrderStatus,
  PendingOrderSortOption,
  PendingUpdateListItem,
  PendingUpdateDetail,
  PendingUpdatesByOrder,
  PendingUpdateSortOption,
  PendingUpdateStatus,
  OrderHistory,
  ActionType,
  UnifiedActionListItem,
  UnifiedActionListResponse,
  MarkReadRequest,
  MarkReadResponse,
} from '../types';

// =============================================================================
// Pending Orders API
// =============================================================================

/**
 * Query params for GET /order-management/pending-orders
 */
export interface GetPendingOrdersParams {
  /** Search by HAWB */
  search?: string;

  /** Filter by status */
  status?: PendingOrderStatus | 'all';

  /** Filter by customer */
  customer_id?: number;

  /** Sort option */
  sort_by?: string;
  sort_order?: 'asc' | 'desc';

  /** Pagination */
  limit?: number;
  offset?: number;
}

/**
 * Response for GET /order-management/pending-orders
 */
export interface GetPendingOrdersResponse {
  items: PendingOrderListItem[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Response for GET /order-management/pending-orders/{id}
 */
export type GetPendingOrderDetailResponse = PendingOrderDetail;

/**
 * Request for POST /order-management/pending-orders/{id}/confirm-field
 */
export interface ConfirmFieldRequest {
  field_name: string;
  history_id: number;
}

/**
 * Response for POST /order-management/pending-orders/{id}/confirm-field
 */
export interface ConfirmFieldResponse {
  success: boolean;
  field_name: string;
  selected_value: string;
  new_status: PendingOrderStatus;
  message?: string;
}

// =============================================================================
// Pending Updates API (New Schema)
// =============================================================================

/**
 * Query params for GET /order-management/pending-updates
 */
export interface GetPendingUpdatesParams {
  /** Filter by status */
  status?: PendingUpdateStatus | 'all';

  /** Filter by customer */
  customer_id?: number;

  /** Filter by HAWB */
  hawb?: string;

  /** Pagination */
  limit?: number;
  offset?: number;
}

/**
 * Response for GET /order-management/pending-updates
 */
export interface GetPendingUpdatesResponse {
  items: PendingUpdateListItem[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Response for GET /order-management/pending-updates/{id}
 */
export type GetPendingUpdateDetailResponse = PendingUpdateDetail;

/**
 * Request for POST /order-management/pending-updates/{id}/approve
 */
export interface ApprovePendingUpdateRequest {
  // Currently no body needed
}

/**
 * Response for POST /order-management/pending-updates/{id}/approve
 */
export interface ApprovePendingUpdateResponse {
  success: boolean;
  update_id: number;
  htc_order_number: number | null;
  new_status: string;
  fields_updated: string[];
  message?: string;
}

/**
 * Request for POST /order-management/pending-updates/{id}/reject
 */
export interface RejectPendingUpdateRequest {
  reason?: string;
}

/**
 * Response for POST /order-management/pending-updates/{id}/reject
 */
export interface RejectPendingUpdateResponse {
  success: boolean;
  update_id: number;
  new_status: string;
  message?: string;
}

/**
 * Request for POST /order-management/pending-updates/{id}/confirm-field
 */
export interface ConfirmUpdateFieldRequest {
  field_name: string;
  history_id: number;
}

/**
 * Response for POST /order-management/pending-updates/{id}/confirm-field
 */
export interface ConfirmUpdateFieldResponse {
  success: boolean;
  field_name: string;
  selected_value: string;
  message?: string;
}

/**
 * Request for POST /order-management/pending-updates/bulk-approve
 */
export interface BulkApprovePendingUpdatesRequest {
  update_ids: number[];
}

/**
 * Request for POST /order-management/pending-updates/bulk-reject
 */
export interface BulkRejectPendingUpdatesRequest {
  update_ids: number[];
  reason?: string;
}

/**
 * Response for approve/reject operations (legacy compatibility)
 */
export interface PendingUpdateActionResponse {
  success: boolean;
  update_id: number;
  new_status: string;
  message?: string;
}

/**
 * Response for bulk operations
 */
export interface BulkPendingUpdateActionResponse {
  success_count: number;
  failure_count: number;
  results: PendingUpdateActionResponse[];
}

/**
 * Legacy: Response for grouped updates (deprecated)
 * @deprecated
 */
export interface GetPendingUpdatesGroupedResponse {
  items: PendingUpdatesByOrder[];
  total_orders: number;
  total_updates: number;
}

// =============================================================================
// Order History API
// =============================================================================

/**
 * Query params for GET /order-management/orders/{hawb}/history
 */
export interface GetOrderHistoryParams {
  /** The HAWB to get history for */
  hawb: string;
}

/**
 * Response for GET /order-management/orders/{hawb}/history
 */
export type GetOrderHistoryResponse = OrderHistory;

// =============================================================================
// Unified Actions API
// =============================================================================

/**
 * Query params for GET /order-management/unified-actions
 */
export interface GetUnifiedActionsParams {
  /** Filter by action type */
  type?: ActionType | 'all';

  /** Filter by status (varies by type) */
  status?: string;

  /** Filter by read/unread state */
  is_read?: boolean;

  /** Pagination */
  limit?: number;
  offset?: number;
}

/**
 * Response for GET /order-management/unified-actions
 */
export { UnifiedActionListResponse as GetUnifiedActionsResponse };

/**
 * Request for POST /order-management/mark-read
 */
export { MarkReadRequest };

/**
 * Response for POST /order-management/mark-read
 */
export { MarkReadResponse };
