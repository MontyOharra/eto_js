/**
 * Router Configuration
 * Centralized TanStack Router setup
 */

import { createRouter, createHashHistory } from '@tanstack/react-router';
import { routeTree } from '../routeTree.gen';

// Create hash history for Electron (file:// protocol)
const hashHistory = createHashHistory();

// Create router instance
export const router = createRouter({
  routeTree,
  history: hashHistory,
  defaultPreload: 'intent',
  defaultPreloadStaleTime: 0,
});

// Register the router for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
