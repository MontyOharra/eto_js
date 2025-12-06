/**
 * OrderHistoryTimeline Component
 *
 * Displays the full history of an order as a timeline of events.
 */

import type { OrderHistory, OrderHistoryEvent, ContributionType } from '../../types';
import { OrderStatusBadge } from '../OrderStatusBadge';

interface OrderHistoryTimelineProps {
  history: OrderHistory;
  onBack: () => void;
  onViewRun: (runId: number) => void;
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

const eventTypeConfig: Record<
  ContributionType,
  { label: string; color: string; icon: React.ReactNode }
> = {
  created_pending: {
    label: 'Created Pending Order',
    color: 'blue',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
      </svg>
    ),
  },
  added_fields: {
    label: 'Added Fields',
    color: 'green',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
      </svg>
    ),
  },
  overwrote_fields: {
    label: 'Overwrote Fields',
    color: 'yellow',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
  },
  triggered_creation: {
    label: 'Order Created in HTC',
    color: 'emerald',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  proposed_update: {
    label: 'Proposed Update',
    color: 'purple',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
    ),
  },
};

function getColorClasses(color: string) {
  const colors: Record<string, { bg: string; border: string; text: string }> = {
    blue: { bg: 'bg-blue-500/20', border: 'border-blue-500', text: 'text-blue-400' },
    green: { bg: 'bg-green-500/20', border: 'border-green-500', text: 'text-green-400' },
    yellow: { bg: 'bg-yellow-500/20', border: 'border-yellow-500', text: 'text-yellow-400' },
    emerald: { bg: 'bg-emerald-500/20', border: 'border-emerald-500', text: 'text-emerald-400' },
    purple: { bg: 'bg-purple-500/20', border: 'border-purple-500', text: 'text-purple-400' },
  };
  return colors[color] || colors.blue;
}

interface TimelineEventProps {
  event: OrderHistoryEvent;
  onViewRun: (runId: number) => void;
  isLast: boolean;
}

function TimelineEvent({ event, onViewRun, isLast }: TimelineEventProps) {
  const config = eventTypeConfig[event.event_type];
  const colors = getColorClasses(config.color);

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-[15px] top-8 bottom-0 w-0.5 bg-gray-700" />
      )}

      {/* Icon */}
      <div
        className={`relative z-10 flex items-center justify-center w-8 h-8 rounded-full ${colors.bg} ${colors.text} border-2 ${colors.border} flex-shrink-0`}
      >
        {config.icon}
      </div>

      {/* Content */}
      <div className="flex-1 pb-6">
        <div className="flex items-center justify-between mb-1">
          <span className={`font-medium ${colors.text}`}>{config.label}</span>
          <span className="text-xs text-gray-500">{formatDate(event.timestamp)}</span>
        </div>

        {/* Source info */}
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={() => onViewRun(event.run_id)}
            className="text-sm text-blue-400 hover:text-blue-300 hover:underline"
          >
            Run #{event.run_id}
          </button>
          <span className="text-gray-600">•</span>
          <span className="text-sm text-gray-500 truncate max-w-[200px]">
            {event.pdf_filename}
          </span>
          {event.template_name && (
            <>
              <span className="text-gray-600">•</span>
              <span className="text-sm text-gray-500">{event.template_name}</span>
            </>
          )}
        </div>

        {/* Fields affected */}
        {event.fields_affected.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-3 space-y-2">
            {event.fields_affected.map((field) => {
              const prevValue = event.previous_values?.[field];
              const newValue = event.new_values[field];
              const hasChange = prevValue !== undefined;

              return (
                <div key={field} className="flex items-center gap-2 text-sm">
                  <span className="text-gray-400 min-w-[120px]">
                    {formatFieldName(field)}:
                  </span>
                  {hasChange ? (
                    <>
                      <span className="text-red-400/70 line-through font-mono">
                        {String(prevValue) || '(empty)'}
                      </span>
                      <svg
                        className="w-4 h-4 text-gray-500 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M17 8l4 4m0 0l-4 4m4-4H3"
                        />
                      </svg>
                      <span className="text-green-400 font-mono">
                        {String(newValue)}
                      </span>
                    </>
                  ) : (
                    <span className="text-green-400 font-mono">
                      {String(newValue)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Notes */}
        {event.notes && (
          <p className="mt-2 text-sm text-gray-500 italic">{event.notes}</p>
        )}
      </div>
    </div>
  );
}

export function OrderHistoryTimeline({
  history,
  onBack,
  onViewRun,
}: OrderHistoryTimelineProps) {
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
              <h2 className="text-xl font-bold text-white">Order History</h2>
              <span className="font-mono text-lg text-gray-300">{history.hawb}</span>
              <OrderStatusBadge status={history.status} />
            </div>
            <p className="text-gray-400 text-sm mt-1">
              {history.customer_name}
              {history.htc_order_number && (
                <span className="ml-2 text-green-400">
                  (Order #{history.htc_order_number})
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl mx-auto">
          {/* Timeline */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-white mb-4">Timeline</h3>
            {history.events.length === 0 ? (
              <div className="text-gray-500 text-center py-8">
                No events recorded yet
              </div>
            ) : (
              <div>
                {history.events.map((event, index) => (
                  <TimelineEvent
                    key={event.id}
                    event={event}
                    onViewRun={onViewRun}
                    isLast={index === history.events.length - 1}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Pending Updates */}
          {history.pending_updates.length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-white mb-4">
                Pending Updates ({history.pending_updates.length})
              </h3>
              <div className="bg-gray-800 rounded-lg p-4 space-y-3">
                {history.pending_updates.map((update) => (
                  <div
                    key={update.id}
                    className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-300">
                        {update.field_label}
                      </span>
                      <span className="text-sm text-gray-500 font-mono">
                        {update.current_value || '(empty)'}
                      </span>
                      <svg
                        className="w-4 h-4 text-gray-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M17 8l4 4m0 0l-4 4m4-4H3"
                        />
                      </svg>
                      <span className="text-sm text-yellow-400 font-mono">
                        {update.proposed_value}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatDate(update.proposed_at)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Current Field Values */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">
              Current Field Values
            </h3>
            <div className="bg-gray-800 rounded-lg p-4">
              {Object.keys(history.current_field_values).length === 0 ? (
                <div className="text-gray-500 text-center py-4">
                  No field values set
                </div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(history.current_field_values).map(
                    ([key, value]) => (
                      <div
                        key={key}
                        className="flex justify-between py-2 border-b border-gray-700 last:border-0"
                      >
                        <span className="text-gray-400">
                          {formatFieldName(key)}
                        </span>
                        <span className="text-white font-mono">
                          {String(value) || '-'}
                        </span>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
