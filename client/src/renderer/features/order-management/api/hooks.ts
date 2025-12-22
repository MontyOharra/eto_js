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

  // Unified Actions
  unifiedActions: () => [...orderManagementQueryKeys.all, 'unified-actions'] as const,
  unifiedActionsList: (params?: GetUnifiedActionsParams) =>
    [...orderManagementQueryKeys.unifiedActions(), 'list', params] as const,

  // Order History
  orderHistory: () => [...orderManagementQueryKeys.all, 'history'] as const,
  orderHistoryByHawb: (hawb: string) =>
    [...orderManagementQueryKeys.orderHistory(), hawb] as const,
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
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch detail for a single pending order
 */
export function usePendingOrderDetail(id: number | null) {
  return useQuery({
    queryKey: orderManagementQueryKeys.pendingOrderDetail(id!),
    queryFn: async (): Promise<GetPendingOrderDetailResponse> => {
      const response = await apiClient.get<GetPendingOrderDetailResponse>(
        `${baseUrl}/pending-orders/${id}`
      );
      return response.data;
    },
    enabled: id !== null,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

/**
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
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch detail for a single pending update
 */
export function usePendingUpdateDetail(id: number | null) {
  return useQuery({
    queryKey: orderManagementQueryKeys.pendingUpdateDetail(id!),
    queryFn: async (): Promise<GetPendingUpdateDetailResponse> => {
      const response = await apiClient.get<GetPendingUpdateDetailResponse>(
        `${baseUrl}/pending-updates/${id}`
      );
      return response.data;
    },
    enabled: id !== null,
    staleTime: 30 * 1000,
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
// Unified Actions Hooks
// ============================================================================

/**
 * Fetch unified list of pending orders and updates
 */
export function useUnifiedActions(params?: GetUnifiedActionsParams) {
  return useQuery({
    queryKey: orderManagementQueryKeys.unifiedActionsList(params),
    queryFn: async (): Promise<GetUnifiedActionsResponse> => {
      const response = await apiClient.get<GetUnifiedActionsResponse>(
        `${baseUrl}/unified-actions`,
        { params }
      );
      return response.data;
    },
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Mark an item as read or unread
 */
export function useMarkRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: MarkReadRequest): Promise<MarkReadResponse> => {
      const response = await apiClient.post<MarkReadResponse>(
        `${baseUrl}/mark-read`,
        request
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate unified actions list
      queryClient.invalidateQueries({
        queryKey: orderManagementQueryKeys.unifiedActions(),
      });
      // Also invalidate the specific type's list
      if (variables.type === 'create') {
        queryClient.invalidateQueries({
          queryKey: orderManagementQueryKeys.pendingOrders(),
        });
      } else {
        queryClient.invalidateQueries({
          queryKey: orderManagementQueryKeys.pendingUpdates(),
        });
      }
    },
  });
}
