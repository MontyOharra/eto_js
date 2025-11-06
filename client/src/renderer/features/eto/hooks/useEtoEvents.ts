/**
 * useEtoEvents Hook
 * Connects to Server-Sent Events (SSE) endpoint for real-time ETO run updates
 *
 * Automatically connects when component mounts and reconnects if connection drops.
 * Provides callbacks for run_created, run_updated, and run_deleted events.
 */

import { useEffect, useRef, useCallback } from 'react';
import { API_CONFIG } from '../../../shared/api/config';

interface EtoEvent {
  type: 'run_created' | 'run_updated' | 'run_deleted';
  data: {
    id: number;
    pdf_file_id?: number;
    status?: string;
    processing_step?: string | null;
    started_at?: string;
    completed_at?: string;
    created_at?: string;
    error_type?: string | null;
    error_message?: string | null;
  };
  timestamp: string;
}

interface UseEtoEventsProps {
  onRunCreated?: (data: EtoEvent['data']) => void;
  onRunUpdated?: (data: EtoEvent['data']) => void;
  onRunDeleted?: (runId: number) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

export function useEtoEvents({
  onRunCreated,
  onRunUpdated,
  onRunDeleted,
  onConnected,
  onDisconnected,
}: UseEtoEventsProps) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isConnectedRef = useRef(false);

  const connect = useCallback(() => {
    // Don't create duplicate connections
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      return;
    }

    // Create EventSource connection
    const eventSource = new EventSource(
      `${API_CONFIG.BASE_URL}/api/eto-runs/events`,
      {
        withCredentials: false, // No credentials needed for same-origin
      }
    );

    eventSource.onopen = () => {
      isConnectedRef.current = true;
      onConnected?.();
    };

    eventSource.onmessage = (event) => {
      try {
        // Parse the event data
        const payload: EtoEvent = JSON.parse(event.data);

        // Route to appropriate callback
        switch (payload.type) {
          case 'run_created':
            onRunCreated?.(payload.data);
            break;

          case 'run_updated':
            onRunUpdated?.(payload.data);
            break;

          case 'run_deleted':
            onRunDeleted?.(payload.data.id);
            break;

          default:
            console.warn('[SSE] Unknown event type:', payload.type);
        }
      } catch (err) {
        console.error('[SSE] Error parsing event:', err);
      }
    };

    eventSource.onerror = (error) => {

      // Update connection state
      if (isConnectedRef.current) {
        isConnectedRef.current = false;
        onDisconnected?.();
      }

      // Close current connection
      eventSource.close();

      // Attempt reconnect after delay
      if (!reconnectTimeoutRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectTimeoutRef.current = null;
          connect();
        }, 3000); // Retry after 3 seconds
      }
    };

    eventSourceRef.current = eventSource;
  }, [onRunCreated, onRunUpdated, onRunDeleted, onConnected, onDisconnected]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Close connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      isConnectedRef.current = false;
    };
  }, [connect]);

  return {
    isConnected: isConnectedRef.current,
  };
}
