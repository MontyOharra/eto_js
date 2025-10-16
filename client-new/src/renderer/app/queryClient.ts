/**
 * React Query Client Configuration
 * Configures default options for queries and mutations
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time: how long data is considered fresh (5 minutes)
      staleTime: 1000 * 60 * 5,

      // Cache time: how long unused data stays in cache (10 minutes)
      gcTime: 1000 * 60 * 10,

      // Retry failed requests
      retry: 1,

      // Refetch on window focus in production only
      refetchOnWindowFocus: !import.meta.env.DEV,

      // Refetch on reconnect
      refetchOnReconnect: true,
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
});
