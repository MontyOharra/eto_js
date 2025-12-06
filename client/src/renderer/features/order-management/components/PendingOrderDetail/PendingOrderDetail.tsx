/**
 * PendingOrderDetail Component
 *
 * Shows detailed view of a pending order with all fields and contributing runs.
 */

import type { PendingOrderDetail as PendingOrderDetailType } from '../../types';
import { OrderStatusBadge } from '../OrderStatusBadge';
import { FieldStatusBadge } from '../FieldStatusBadge';

interface PendingOrderDetailProps {
  order: PendingOrderDetailType;
  onBack: () => void;
  onViewHistory: (hawb: string) => void;
}

function formatDate(isoDate: string | null): string {
  if (!isoDate) return '-';
  try {
    const date = new Date(isoDate);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoDate;
  }
}

function formatFieldName(fieldName: string): string {
  return fieldName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function PendingOrderDetail({
  order,
  onBack,
  onViewHistory,
}: PendingOrderDetailProps) {
  return (
    <div className="h-full flex flex-col overflow-hidden bg-gray-900">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-white font-mono">
                {order.hawb}
              </h2>
              <OrderStatusBadge status={order.status} />
            </div>
            <p className="text-gray-400 text-sm mt-1">
              {order.customer_name} (ID: {order.customer_id})
            </p>
          </div>
        </div>
        <button
          onClick={() => onViewHistory(order.hawb)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          View Full History
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="grid grid-cols-2 gap-6">
          {/* Left Column - Field Values */}
          <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-4">
              Order Fields
            </h3>
            <div className="mb-4">
              <FieldStatusBadge fieldStatus={order.field_status} detailed />
            </div>
            <div className="space-y-3">
              {Object.entries(order.field_values).map(([key, value]) => (
                <div
                  key={key}
                  className="flex justify-between items-start py-2 border-b border-gray-700"
                >
                  <span className="text-gray-400 text-sm">
                    {formatFieldName(key)}
                  </span>
                  <span className="text-white text-sm text-right max-w-[60%]">
                    {String(value) || '-'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right Column - Contributing Runs */}
          <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-4">
              Contributing Runs ({order.contributing_runs.length})
            </h3>
            <div className="space-y-3">
              {order.contributing_runs.map((run) => (
                <div
                  key={`${run.run_id}-${run.sub_run_id}`}
                  className="p-3 bg-gray-700/50 rounded-lg"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-white">
                      Run #{run.run_id}
                    </span>
                    <span className="text-xs text-gray-400">
                      {formatDate(run.contributed_at)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mb-2">
                    {run.pdf_filename}
                  </p>
                  {run.template_name && (
                    <p className="text-xs text-gray-500 mb-2">
                      Template: {run.template_name}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-1">
                    {run.fields_contributed.map((field) => (
                      <span
                        key={field}
                        className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded"
                      >
                        {formatFieldName(field)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Order Metadata */}
        <div className="mt-6 bg-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Metadata</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Created:</span>
              <span className="text-white ml-2">
                {formatDate(order.created_at)}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Last Updated:</span>
              <span className="text-white ml-2">
                {formatDate(order.updated_at)}
              </span>
            </div>
            {order.htc_order_number && (
              <div>
                <span className="text-gray-400">HTC Order #:</span>
                <span className="text-green-400 font-mono ml-2">
                  {order.htc_order_number}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
