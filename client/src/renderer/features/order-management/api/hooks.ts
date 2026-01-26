/**
 * Order Management API Hooks
 * TanStack Query hooks for order management operations
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type {
  GetPendingOrdersParams,
  GetPendingOrdersResponse,
  GetPendingOrderDetailResponse,
  GetPendingActionDetailResponse,
  ConfirmFieldRequest,
  ConfirmFieldResponse,
  GetPendingUpdatesParams,
  GetPendingUpdatesResponse,
  GetPendingUpdateDetailResponse,
  ApprovePendingUpdateRequest,
  ApprovePendingUpdateResponse,
  RejectPendingUpdateRequest,
  RejectPendingUpdateResponse,
  ConfirmUpdateFieldRequest,
  ConfirmUpdateFieldResponse,
  BulkApprovePendingUpdatesRequest,
  BulkRejectPendingUpdatesRequest,
  PendingUpdateActionResponse,
  BulkPendingUpdateActionResponse,
  GetOrderHistoryResponse,
  GetUnifiedActionsParams,
  GetUnifiedActionsResponse,
  MarkReadRequest,
  MarkReadResponse,
  SetFieldValueRequest,
  SetFieldValueResponse,
  GetAddressesResponse,
  GetAddressesParams,
} from './types';
import type { ActionType } from '../types';

// Base URL for order management endpoints
// TODO: Add to API_CONFIG when backend is ready
const baseUrl = '/api/order-management';

// ============================================================================
// Query Keys
// ============================================================================

export const orderManagementQueryKeys = {
  all: ['order-management'] as const,

  // Pending Orders
  pendingOrders: () => [...orderManagementQueryKeys.all, 'pending-orders'] as const,
  pendingOrdersList: (params?: GetPendingOrdersParams) =>
    [...orderManagementQueryKeys.pendingOrders(), 'list', params] as const,
  pendingOrderDetail: (id: number) =>
    [...orderManagementQueryKeys.pendingOrders(), 'detail', id] as const,

  // Pending Updates
  pendingUpdates: () => [...orderManagementQueryKeys.all, 'pending-updates'] as const,
  pendingUpdatesList: (params?: GetPendingUpdatesParams) =>
    [...orderManagementQueryKeys.pendingUpdates(), 'list', params] as const,
  pendingUpdateDetail: (id: number) =>
    [...orderManagementQueryKeys.pendingUpdates(), 'detail', id] as const,

  // Unified Actions (Pending Actions)
  pendingActions: () => [...orderManagementQueryKeys.all, 'pending-actions'] as const,
  pendingActionsList: (params?: GetUnifiedActionsParams) =>
    [...orderManagementQueryKeys.pendingActions(), 'list', params] as const,
  pendingActionDetail: (id: number) =>
    [...orderManagementQueryKeys.pendingActions(), 'detail', id] as const,

  // Legacy aliases for unified actions
  unifiedActions: () => orderManagementQueryKeys.pendingActions(),
  unifiedActionsList: (params?: GetUnifiedActionsParams) =>
    orderManagementQueryKeys.pendingActionsList(params),

  // Order History
  orderHistory: () => [...orderManagementQueryKeys.all, 'history'] as const,
  orderHistoryByHawb: (hawb: string) =>
    [...orderManagementQueryKeys.orderHistory(), hawb] as const,

  // Addresses (for location field dropdowns)
  addresses: () => [...orderManagementQueryKeys.all, 'addresses'] as const,
};

// ============================================================================
// Pending Orders Hooks
// ============================================================================

/**
 * Fetch list of pending orders with filtering and pagination
 */
export function usePendingOrders(params?: GetPendingOrdersParams) {
  return useQuery({
    queryKey: orderManagementQueryKeys.pendingOrdersList(params),
    queryFn: async (): Promise<GetPendingOrdersResponse> => {
      const response = await apiClient.get<GetPendingOrdersResponse>(
        `${baseUrl}/pending-orders`,
        { params }
      );
      return response.data;
    },
    placeholderData: keepPreviousData,
    staleTime: 0, // Real-time updates via SSE
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch detail for a single pending order (create action)
 */
export function usePendingOrderDetail(id: number | null) {
  return useQuery({
    queryKey: orderManagementQueryKeys.pendingOrderDetail(id!),
    queryFn: async (): Promise<GetPendingActionDetailResponse> => {
      const response = await apiClient.get<GetPendingActionDetailResponse>(
        `/api/pending-actions/${id}`
      );
      return response.data;
    },
    enabled: id !== null,
    staleTime: 0, // Real-time updates via SSE
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * @deprecated Use useSelectFieldValue instead
 * Confirm a field selection to resolve a conflict
 */
export function useConfirmField() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      pendingOrderId,
      fieldName,
      historyId,
    }: {
      pendingOrderId: number;
      fieldName: string;
      historyId: number;
    }): Promise<ConfirmFieldResponse> => {
      const response = await apiClient.post<ConfirmFieldResponse>(
        `${baseUrl}/pending-orders/${pendingOrderId}/confirm-field`,
        { field_name: fieldName, history_id: historyId }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate the specific order detail to refetch with new state
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrderDetail(variables.pendingOrderId),
      });
      // Also invalidate the list in case status changed
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrders(),
      });
    },
  });
}

/**
 * Select a field value (resolve conflict or change selection)
 * Uses the new unified /pending-actions/{id}/select-field endpoint
 */
export function useSelectFieldValue() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      actionId,
      fieldId,
    }: {
      actionId: number;
      fieldId: number;
    }): Promise<{
      pending_action_id: number;
      field_id: number;
      field_name: string;
      new_status: string;
      success: boolean;
      message: string | null;
    }> => {
      const response = await apiClient.post(
        `/api/pending-actions/${actionId}/select-field`,
        { field_id: fieldId }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate all related queries (both create and update detail views)
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActionDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrderDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdateDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActions(),
      });
    },
  });
}

/**
 * Set field approval status for updates (include/exclude field from update)
 */
export function useSetFieldApproval() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      actionId,
      fieldName,
      isApproved,
    }: {
      actionId: number;
      fieldName: string;
      isApproved: boolean;
    }): Promise<{
      pending_action_id: number;
      field_name: string;
      is_approved: boolean;
      success: boolean;
      message: string | null;
    }> => {
      const response = await apiClient.post(
        `/api/pending-actions/${actionId}/set-field-approval`,
        { field_name: fieldName, is_approved: isApproved }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate all detail query patterns for compatibility
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActionDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrderDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdateDetail(variables.actionId),
      });
      // Also invalidate the list in case status changed
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActions(),
      });
    },
  });
}

/**
 * Response type for approve action endpoint
 */
export interface ApproveActionResponse {
  pending_action_id: number;
  success: boolean;
  action_type: string;
  htc_order_number: number | null;
  new_status: string;
  message: string | null;
  requires_review: boolean;
  review_reason: string | null;
}

/**
 * Approve a pending action (unified - works for both creates and updates)
 * Uses the new /pending-actions/{id}/approve endpoint
 *
 * If requires_review is true in the response, the action was NOT approved
 * and remains in its current status. The caller should show the review_reason
 * to the user and refresh the detail view.
 */
export function useApprovePendingAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      actionId,
      detailViewedAt,
      approverUserId,
    }: {
      actionId: number;
      detailViewedAt?: string; // ISO timestamp of when user viewed detail page
      approverUserId?: string; // User ID of approver for audit trail
    }): Promise<ApproveActionResponse> => {
      const response = await apiClient.post(
        `/api/pending-actions/${actionId}/approve`,
        { detail_viewed_at: detailViewedAt, approver_user_id: approverUserId }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate all related queries - use all detail key patterns for compatibility
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActionDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrderDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdateDetail(variables.actionId),
      });
      // Invalidate list queries
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActions(),
      });
    },
  });
}

/**
 * Reject a pending action (unified - works for both creates and updates)
 * Uses the new /pending-actions/{id}/reject endpoint
 */
export function useRejectPendingAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      actionId,
      reason,
    }: {
      actionId: number;
      reason?: string;
    }): Promise<{
      pending_action_id: number;
      success: boolean;
      new_status: string;
      message: string | null;
    }> => {
      const response = await apiClient.post(
        `/api/pending-actions/${actionId}/reject`,
        { reason }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate all related queries - use all detail key patterns for compatibility
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActionDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrderDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdateDetail(variables.actionId),
      });
      // Invalidate list queries
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActions(),
      });
    },
  });
}

/**
 * @deprecated Use useApprovePendingAction instead
 * Approve a pending order and create it in HTC
 */
export function useApprovePendingOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      pendingOrderId,
      approverUsername,
    }: {
      pendingOrderId: number;
      approverUsername: string;
    }): Promise<{ success: boolean; pending_order_id: number; htc_order_number?: number; new_status: string; message?: string }> => {
      const response = await apiClient.post(
        `${baseUrl}/pending-orders/${pendingOrderId}/approve`,
        { approver_username: approverUsername }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate the specific order detail
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrderDetail(variables.pendingOrderId),
      });
      // Invalidate the list
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrders(),
      });
      // Invalidate unified actions
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.unifiedActions(),
      });
    },
  });
}

/**
 * @deprecated Use useRejectPendingAction instead
 * Reject a pending order
 */
export function useRejectPendingOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      pendingOrderId,
      reason,
    }: {
      pendingOrderId: number;
      reason?: string;
    }): Promise<{ success: boolean; pending_order_id: number; new_status: string; message?: string }> => {
      const response = await apiClient.post(
        `${baseUrl}/pending-orders/${pendingOrderId}/reject`,
        { reason }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate the specific order detail
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrderDetail(variables.pendingOrderId),
      });
      // Invalidate the list
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrders(),
      });
      // Invalidate unified actions
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.unifiedActions(),
      });
    },
  });
}

// ============================================================================
// Pending Updates Hooks
// ============================================================================

/**
 * Fetch list of pending updates
 */
export function usePendingUpdates(params?: GetPendingUpdatesParams) {
  return useQuery({
    queryKey: orderManagementQueryKeys.pendingUpdatesList(params),
    queryFn: async (): Promise<GetPendingUpdatesResponse> => {
      const response = await apiClient.get<GetPendingUpdatesResponse>(
        `${baseUrl}/pending-updates`,
        { params }
      );
      return response.data;
    },
    placeholderData: keepPreviousData,
    staleTime: 0, // Real-time updates via SSE
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch detail for a single pending update
 */
export function usePendingUpdateDetail(id: number | null) {
  return useQuery({
    queryKey: orderManagementQueryKeys.pendingUpdateDetail(id!),
    queryFn: async (): Promise<GetPendingActionDetailResponse> => {
      const response = await apiClient.get<GetPendingActionDetailResponse>(
        `/api/pending-actions/${id}`
      );
      return response.data;
    },
    enabled: id !== null,
    staleTime: 0, // Real-time updates via SSE
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Approve a single pending update
 */
export function useApprovePendingUpdate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      updateId,
      approverUsername,
    }: {
      updateId: number;
      approverUsername: string;
    }): Promise<ApprovePendingUpdateResponse> => {
      const response = await apiClient.post<ApprovePendingUpdateResponse>(
        `${baseUrl}/pending-updates/${updateId}/approve`,
        { approver_username: approverUsername }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingUpdates() });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdateDetail(variables.updateId)
      });
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.orderHistory() });
    },
  });
}

/**
 * Reject a single pending update
 */
export function useRejectPendingUpdate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      updateId,
    }: {
      updateId: number;
    }): Promise<RejectPendingUpdateResponse> => {
      const response = await apiClient.post<RejectPendingUpdateResponse>(
        `${baseUrl}/pending-updates/${updateId}/reject`
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingUpdates() });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdateDetail(variables.updateId)
      });
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.orderHistory() });
    },
  });
}

/**
 * @deprecated Use useSelectFieldValue instead
 * Confirm a field selection to resolve a conflict in a pending update
 */
export function useConfirmUpdateField() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      pendingUpdateId,
      fieldName,
      historyId,
    }: {
      pendingUpdateId: number;
      fieldName: string;
      historyId: number;
    }): Promise<ConfirmUpdateFieldResponse> => {
      const response = await apiClient.post<ConfirmUpdateFieldResponse>(
        `${baseUrl}/pending-updates/${pendingUpdateId}/confirm-field`,
        { field_name: fieldName, history_id: historyId }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdateDetail(variables.pendingUpdateId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdates(),
      });
    },
  });
}

/**
 * Bulk approve multiple pending updates
 */
export function useBulkApprovePendingUpdates() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: BulkApprovePendingUpdatesRequest
    ): Promise<BulkPendingUpdateActionResponse> => {
      const response = await apiClient.post<BulkPendingUpdateActionResponse>(
        `${baseUrl}/pending-updates/bulk-approve`,
        request
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingUpdates() });
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.orderHistory() });
    },
  });
}

/**
 * Bulk reject multiple pending updates
 */
export function useBulkRejectPendingUpdates() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: BulkRejectPendingUpdatesRequest
    ): Promise<BulkPendingUpdateActionResponse> => {
      const response = await apiClient.post<BulkPendingUpdateActionResponse>(
        `${baseUrl}/pending-updates/bulk-reject`,
        request
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingUpdates() });
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.orderHistory() });
    },
  });
}

// ============================================================================
// Order History Hooks
// ============================================================================

/**
 * Fetch order history by HAWB
 */
export function useOrderHistory(hawb: string | null) {
  return useQuery({
    queryKey: orderManagementQueryKeys.orderHistoryByHawb(hawb!),
    queryFn: async (): Promise<GetOrderHistoryResponse> => {
      const response = await apiClient.get<GetOrderHistoryResponse>(
        `${baseUrl}/orders/${encodeURIComponent(hawb!)}/history`
      );
      return response.data;
    },
    enabled: hawb !== null && hawb.length > 0,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

// ============================================================================
// Pending Actions Hooks (replaces old unified-actions)
// ============================================================================

/**
 * Fetch list of pending actions (unified orders and updates)
 */
export function usePendingActions(params?: GetUnifiedActionsParams) {
  return useQuery({
    queryKey: orderManagementQueryKeys.unifiedActionsList(params),
    queryFn: async (): Promise<GetUnifiedActionsResponse> => {
      // Map the params to match the new API parameter names
      const apiParams: Record<string, unknown> = {};
      if (params?.action_type && params.action_type !== 'all') {
        apiParams.action_type = params.action_type;
      }
      if (params?.status) {
        apiParams.status = params.status;
      }
      if (params?.is_read !== undefined) {
        apiParams.is_read = params.is_read;
      }
      if (params?.customer_id !== undefined) {
        apiParams.customer_id = params.customer_id;
      }
      if (params?.search) {
        apiParams.search = params.search;
      }
      if (params?.limit !== undefined) {
        apiParams.limit = params.limit;
      }
      if (params?.offset !== undefined) {
        apiParams.offset = params.offset;
      }
      if (params?.sort_by) {
        apiParams.sort_by = params.sort_by;
      }
      if (params?.sort_order) {
        apiParams.sort_order = params.sort_order;
      }

      const response = await apiClient.get<GetUnifiedActionsResponse>(
        '/api/pending-actions',
        { params: apiParams }
      );
      return response.data;
    },
    placeholderData: keepPreviousData,
    // No staleTime - always refetch when invalidated for real-time updates
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
  });
}

// Backward compatibility alias
export const useUnifiedActions = usePendingActions;

/**
 * Mark an item as read or unread
 */
export function useMarkRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: MarkReadRequest): Promise<MarkReadResponse> => {
      const response = await apiClient.patch<MarkReadResponse>(
        `/api/pending-actions/${request.id}/read-status`,
        { is_read: request.is_read }
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate unified actions list
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.unifiedActions(),
      });
    },
  });
}

// ============================================================================
// Set Field Value (Manual Entry)
// ============================================================================

/**
 * Mutation to manually set a field value on a pending action.
 * Invalidates the action detail query on success so the UI refreshes.
 */
export function useSetFieldValue() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      actionId,
      ...body
    }: SetFieldValueRequest & { actionId: number }): Promise<SetFieldValueResponse> => {
      const response = await apiClient.post<SetFieldValueResponse>(
        `/api/pending-actions/${actionId}/set-field-value`,
        body
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate all detail key patterns so the UI refreshes with the new field
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActionDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingOrderDetail(variables.actionId),
      });
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingUpdateDetail(variables.actionId),
      });
      // Also invalidate list since status may have changed
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.pendingActions(),
      });
    },
  });
}

// ============================================================================
// Addresses Hooks (for AddFieldModal location dropdowns)
// ============================================================================

/**
 * Fetch addresses with search and pagination.
 * Used by the AddressSearchPicker component.
 */
export function useAddresses(params: GetAddressesParams = {}, enabled = true) {
  return useQuery({
    queryKey: [...orderManagementQueryKeys.addresses(), params] as const,
    queryFn: async (): Promise<GetAddressesResponse> => {
      const response = await apiClient.get<GetAddressesResponse>(
        '/api/pending-actions/addresses',
        { params }
      );
      return response.data;
    },
    enabled,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}
