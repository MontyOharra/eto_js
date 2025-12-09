/**
 * Layout-A Preview Page
 *
 * Preview page for PendingOrderDetailView component with mock data.
 * Used for design validation and testing.
 */

import { createFileRoute } from '@tanstack/react-router';
import { PendingOrderDetailView } from '../../../features/order-management';
import type { PendingOrderDetail } from '../../../features/order-management';

export const Route = createFileRoute('/dashboard/orders/layout-a')({
  component: LayoutAPreviewPage,
});

// =============================================================================
// Mock Data
// =============================================================================

const mockOrder: PendingOrderDetail = {
  id: 1,
  hawb: '123-45678901',
  customer_name: 'ABC Logistics',
  customer_id: 42,
  status: 'incomplete',
  htc_order_number: null,
  created_at: '2025-12-05T14:30:00Z',
  updated_at: '2025-12-05T15:45:00Z',
  htc_created_at: null,
  fields: [
    {
      name: 'hawb',
      label: 'HAWB',
      value: '123-45678901',
      required: true,
      state: 'set',
      conflict_options: null,
      source: { history_id: 1, sub_run_id: 101, contributed_at: '2025-12-05T14:30:00Z' },
    },
    {
      name: 'mawb',
      label: 'MAWB',
      value: '999-12345678',
      required: false,
      state: 'set',
      conflict_options: null,
      source: { history_id: 2, sub_run_id: 102, contributed_at: '2025-12-05T14:35:00Z' },
    },
    {
      name: 'pickup_address',
      label: 'Pickup Address',
      value: '123 Main St, Suite 400, Chicago, IL 60601',
      required: true,
      state: 'set',
      conflict_options: null,
      source: { history_id: 3, sub_run_id: 101, contributed_at: '2025-12-05T14:30:00Z' },
    },
    {
      name: 'pickup_time_start',
      label: 'Pickup Start',
      value: null,
      required: true,
      state: 'conflict',
      conflict_options: [
        { history_id: 4, value: '08:00 AM', sub_run_id: 101, contributed_at: '2025-12-05T14:30:00Z' },
        { history_id: 5, value: '09:00 AM', sub_run_id: 103, contributed_at: '2025-12-05T15:00:00Z' },
      ],
      source: null,
    },
    {
      name: 'pickup_time_end',
      label: 'Pickup End',
      value: '10:00 AM',
      required: true,
      state: 'set',
      conflict_options: null,
      source: { history_id: 6, sub_run_id: 101, contributed_at: '2025-12-05T14:30:00Z' },
    },
    {
      name: 'delivery_address',
      label: 'Delivery Address',
      value: null,
      required: true,
      state: 'empty',
      conflict_options: null,
      source: null,
    },
    {
      name: 'delivery_time_start',
      label: 'Delivery Start',
      value: null,
      required: true,
      state: 'empty',
      conflict_options: null,
      source: null,
    },
    {
      name: 'delivery_time_end',
      label: 'Delivery End',
      value: null,
      required: true,
      state: 'empty',
      conflict_options: null,
      source: null,
    },
    {
      name: 'pickup_notes',
      label: 'Pickup Notes',
      value: 'Call ahead 30 min before arrival',
      required: false,
      state: 'set',
      conflict_options: null,
      source: { history_id: 7, sub_run_id: 101, contributed_at: '2025-12-05T14:30:00Z' },
    },
    {
      name: 'delivery_notes',
      label: 'Delivery Notes',
      value: null,
      required: false,
      state: 'empty',
      conflict_options: null,
      source: null,
    },
    {
      name: 'pieces',
      label: 'Pieces',
      value: '5',
      required: false,
      state: 'set',
      conflict_options: null,
      source: { history_id: 8, sub_run_id: 102, contributed_at: '2025-12-05T14:35:00Z' },
    },
    {
      name: 'weight',
      label: 'Weight',
      value: '125 lbs',
      required: false,
      state: 'set',
      conflict_options: null,
      source: { history_id: 9, sub_run_id: 102, contributed_at: '2025-12-05T14:35:00Z' },
    },
  ],
  contributing_sub_runs: [
    {
      sub_run_id: 101,
      run_id: 1,
      pdf_filename: 'routing_form.pdf',
      template_name: 'SOS Routing Template',
      fields_contributed: ['hawb', 'pickup_address', 'pickup_time_start', 'pickup_time_end', 'pickup_notes'],
      contributed_at: '2025-12-05T14:30:00Z',
    },
    {
      sub_run_id: 102,
      run_id: 1,
      pdf_filename: 'mawb_form.pdf',
      template_name: 'MAWB Template',
      fields_contributed: ['mawb', 'pieces', 'weight'],
      contributed_at: '2025-12-05T14:35:00Z',
    },
    {
      sub_run_id: 103,
      run_id: 2,
      pdf_filename: 'updated_routing.pdf',
      template_name: 'SOS Routing Template',
      fields_contributed: ['pickup_time_start'],
      contributed_at: '2025-12-05T15:00:00Z',
    },
  ],
};

// =============================================================================
// Main Component
// =============================================================================

function LayoutAPreviewPage() {
  const handleBack = () => {
    window.history.back();
  };

  const handleResolveConflict = (fieldName: string, historyId: number) => {
    console.log('Resolve conflict:', fieldName, 'selected history:', historyId);
    alert(`Would resolve conflict for ${fieldName} with history ID ${historyId}`);
  };

  const handleViewHistory = (hawb: string) => {
    console.log('View history for:', hawb);
    alert(`Would navigate to history view for HAWB: ${hawb}`);
  };

  return (
    <PendingOrderDetailView
      order={mockOrder}
      onBack={handleBack}
      onResolveConflict={handleResolveConflict}
      onViewHistory={handleViewHistory}
    />
  );
}
