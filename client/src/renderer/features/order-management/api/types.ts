/**
 * API request/response types for Order Management
 */

import type {
  PendingOrderListItem,
  PendingOrderDetail,
  PendingOrderStatus,
  PendingOrderSortOption,
  PendingUpdateListItem,
  PendingUpdatesByOrder,
  PendingUpdateSortOption,
  OrderHistory,
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

// =============================================================================
// Pending Updates API
// =============================================================================

/**
 * Query params for GET /order-management/pending-updates
 */
export interface GetPendingUpdatesParams {
  /** Filter by HTC order number */
  htc_order_number?: number;

  /** Filter by HAWB */
  hawb?: string;

  /** Group by order (returns PendingUpdatesByOrder[]) */
  group_by_order?: boolean;

  /** Sort option */
  sort_by?: string;
  sort_order?: 'asc' | 'desc';

  /** Pagination */
  limit?: number;
  offset?: number;
}

/**
 * Response for GET /order-management/pending-updates (flat list)
 */
export interface GetPendingUpdatesResponse {
  items: PendingUpdateListItem[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Response for GET /order-management/pending-updates?group_by_order=true
 */
export interface GetPendingUpdatesGroupedResponse {
  items: PendingUpdatesByOrder[];
  total_orders: number;
  total_updates: number;
}

/**
 * Request for POST /order-management/pending-updates/{id}/approve
 */
export interface ApprovePendingUpdateRequest {
  // Currently no body needed, but placeholder for future options
}

/**
 * Request for POST /order-management/pending-updates/{id}/reject
 */
export interface RejectPendingUpdateRequest {
  reason?: string;
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
 * Response for approve/reject operations
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
