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
  GetPendingUpdatesParams,
  GetPendingUpdatesResponse,
  GetPendingUpdatesGroupedResponse,
  ApprovePendingUpdateRequest,
  RejectPendingUpdateRequest,
  BulkApprovePendingUpdatesRequest,
  BulkRejectPendingUpdatesRequest,
  PendingUpdateActionResponse,
  BulkPendingUpdateActionResponse,
  GetOrderHistoryResponse,
} from './types';

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
  pendingUpdatesGrouped: (params?: GetPendingUpdatesParams) =>
    [...orderManagementQueryKeys.pendingUpdates(), 'grouped', params] as const,

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

// ============================================================================
// Pending Updates Hooks
// ============================================================================

/**
 * Fetch list of pending updates (flat list)
 */
export function usePendingUpdates(params?: GetPendingUpdatesParams) {
  return useQuery({
    queryKey: orderManagementQueryKeys.pendingUpdatesList(params),
    queryFn: async (): Promise<GetPendingUpdatesResponse> => {
      const response = await apiClient.get<GetPendingUpdatesResponse>(
        `${baseUrl}/pending-updates`,
        { params: { ...params, group_by_order: false } }
      );
      return response.data;
    },
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch pending updates grouped by order
 */
export function usePendingUpdatesGrouped(params?: Omit<GetPendingUpdatesParams, 'group_by_order'>) {
  return useQuery({
    queryKey: orderManagementQueryKeys.pendingUpdatesGrouped(params),
    queryFn: async (): Promise<GetPendingUpdatesGroupedResponse> => {
      const response = await apiClient.get<GetPendingUpdatesGroupedResponse>(
        `${baseUrl}/pending-updates`,
        { params: { ...params, group_by_order: true } }
      );
      return response.data;
    },
    placeholderData: keepPreviousData,
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
      request,
    }: {
      updateId: number;
      request?: ApprovePendingUpdateRequest;
    }): Promise<PendingUpdateActionResponse> => {
      const response = await apiClient.post<PendingUpdateActionResponse>(
        `${baseUrl}/pending-updates/${updateId}/approve`,
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
 * Reject a single pending update
 */
export function useRejectPendingUpdate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      updateId,
      request,
    }: {
      updateId: number;
      request?: RejectPendingUpdateRequest;
    }): Promise<PendingUpdateActionResponse> => {
      const response = await apiClient.post<PendingUpdateActionResponse>(
        `${baseUrl}/pending-updates/${updateId}/reject`,
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
