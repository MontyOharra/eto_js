import { createFileRoute, Link } from '@tanstack/react-router';
import { PendingOrderDetail } from '../../../features/order-management';
import type { PendingOrderDetail as PendingOrderDetailType } from '../../../features/order-management';

export const Route = createFileRoute('/dashboard/orders/detail-preview')({
  component: DetailPreviewPage,
});

// Mock data for previewing the PendingOrderDetail component
const mockOrderDetail: PendingOrderDetailType = {
  id: 1,
  hawb: '123-45678901',
  customer_id: 42,
  customer_name: 'ABC Logistics',
  status: 'incomplete',
  htc_order_number: null,
  field_values: {
    hawb: '123-45678901',
    mawb: '999-12345678',
    pickup_address: '123 Main St, Suite 400, Chicago, IL 60601',
    pickup_time_start: '08:00 AM',
    pickup_time_end: '10:00 AM',
    delivery_address: null,
    delivery_time_start: null,
    delivery_time_end: null,
    pickup_notes: 'Call ahead 30 min before arrival',
    delivery_notes: null,
    pieces: '5',
    weight: '125 lbs',
  },
  field_status: {
    present: ['hawb', 'mawb', 'pickup_address', 'pickup_time_start', 'pickup_time_end', 'pickup_notes', 'pieces', 'weight'],
    missing_required: ['delivery_address', 'delivery_time_start', 'delivery_time_end'],
    missing_optional: ['delivery_notes'],
  },
  contributing_runs: [
    {
      run_id: 101,
      sub_run_id: 1,
      pdf_filename: 'routing_form.pdf',
      template_name: 'SOS Routing Form',
      fields_contributed: ['hawb', 'pickup_address', 'pickup_time_start', 'pickup_time_end', 'pickup_notes'],
      contributed_at: '2025-12-05T14:30:00Z',
      contribution_type: 'created_pending',
    },
    {
      run_id: 102,
      sub_run_id: 1,
      pdf_filename: 'mawb_form.pdf',
      template_name: 'MAWB Document',
      fields_contributed: ['mawb', 'pieces', 'weight'],
      contributed_at: '2025-12-05T15:45:00Z',
      contribution_type: 'added_fields',
    },
  ],
  created_at: '2025-12-05T14:30:00Z',
  updated_at: '2025-12-05T15:45:00Z',
  htc_created_at: null,
};

function DetailPreviewPage() {
  const handleBack = () => {
    // Navigation handled by Link below
  };

  const handleViewHistory = (hawb: string) => {
    console.log('View history for:', hawb);
    alert(`Would navigate to history view for HAWB: ${hawb}`);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-gray-900">
      {/* Preview Header */}
      <div className="flex-shrink-0 px-6 py-3 bg-purple-900/30 border-b border-purple-500/30 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard/orders"
            className="text-gray-400 hover:text-white transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Orders
          </Link>
          <div className="h-6 w-px bg-gray-700" />
          <span className="text-purple-400 text-sm font-medium">Component Preview Mode</span>
        </div>
        <div className="text-xs text-gray-500">
          Viewing: PendingOrderDetail component with mock data
        </div>
      </div>

      {/* Render the actual component */}
      <div className="flex-1 min-h-0">
        <PendingOrderDetail
          order={mockOrderDetail}
          onBack={handleBack}
          onViewHistory={handleViewHistory}
        />
      </div>
    </div>
  );
}
