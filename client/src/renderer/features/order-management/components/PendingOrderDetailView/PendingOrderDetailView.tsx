/**
 * PendingOrderDetailView Component
 *
 * Detailed view of a pending order with two-column layout:
 * - Left: Order fields with conflict resolution
 * - Right: Contributing data sources
 */

import { useState, useMemo } from 'react';
import type {
  PendingOrderDetail,
  FieldDetail,
  ConflictOption,
  ContributingSubRun,
} from '../../types';

// =============================================================================
// Types
// =============================================================================

interface PendingOrderDetailViewProps {
  order: PendingOrderDetail;
  onBack: () => void;
  onConfirmField: (fieldName: string, historyId: number) => void;
  onViewSubRun: (subRunId: number) => void;
  confirmingFields?: Set<string>; // Fields currently being confirmed
  onApprove?: () => void; // Approve and create order in HTC
  onReject?: () => void; // Reject the pending order
  isApproving?: boolean; // True while approve is in progress
  isRejecting?: boolean; // True while reject is in progress
}

interface LocalFieldState {
  [fieldName: string]: {
    selectedHistoryId: number | null;
    selectedValue: string | null;
  };
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatDate(isoDate: string): string {
  try {
    const date = new Date(isoDate);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoDate;
  }
}

/** Fields that contain datetime values and should be formatted */
const DATETIME_FIELDS = new Set([
  'pickup_time_start',
  'pickup_time_end',
  'delivery_time_start',
  'delivery_time_end',
]);

/**
 * Check if value is a dim object (has height, length, width, qty, weight)
 */
function isDimObject(value: unknown): boolean {
  return (
    typeof value === 'object' &&
    value !== null &&
    'height' in value &&
    'length' in value &&
    'width' in value &&
    'qty' in value &&
    'weight' in value
  );
}

/**
 * Format a single dim object as "qty - HxLxW @weightlbs"
 */
function formatDim(dim: Record<string, unknown>): string {
  const h = dim.height ?? 0;
  const l = dim.length ?? 0;
  const w = dim.width ?? 0;
  const qty = dim.qty ?? 1;
  const weight = dim.weight ?? 0;
  return `${qty} - ${h}x${l}x${w} @${weight}lbs`;
}

/**
 * Try to parse a value as JSON, handling Python-style single quotes
 */
function tryParseJson(value: string): unknown | null {
  try {
    return JSON.parse(value);
  } catch {
    try {
      const jsonified = value.replace(/'/g, '"');
      return JSON.parse(jsonified);
    } catch {
      return null;
    }
  }
}

/**
 * Format a field value for display.
 * For datetime fields, converts ISO string to human-readable format.
 * For dims fields, formats dim objects as human-readable text.
 */
function formatFieldValue(fieldName: string, value: string | null): string | null {
  if (value === null) return null;

  if (DATETIME_FIELDS.has(fieldName)) {
    try {
      const date = new Date(value);
      // Check if valid date
      if (isNaN(date.getTime())) return value;

      return date.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return value;
    }
  }

  // Handle dims field
  if (fieldName === 'dims') {
    const parsed = tryParseJson(value);
    if (parsed !== null) {
      // Check for single dim object
      if (isDimObject(parsed)) {
        return formatDim(parsed as Record<string, unknown>);
      }
      // Check for list[dim] - array of dim objects
      if (Array.isArray(parsed) && parsed.length > 0 && isDimObject(parsed[0])) {
        return '[' + parsed.map((d) => formatDim(d as Record<string, unknown>)).join(', ') + ']';
      }
    }
  }

  return value;
}

// =============================================================================
// Conflict Dropdown Component
// =============================================================================

interface FieldDropdownProps {
  field: FieldDetail;
  localSelection: { selectedHistoryId: number | null; selectedValue: string | null } | undefined;
  onSelect: (fieldName: string, option: ConflictOption) => void;
  isConflict: boolean; // True if unresolved conflict (needs yellow styling)
}

function FieldDropdown({ field, localSelection, onSelect, isConflict }: FieldDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const options = field.conflict_options ?? [];

  // Determine the display value:
  // 1. If user has made a local selection, use that
  // 2. Otherwise, use the field's current value (which is the confirmed/set value)
  const localSelectedOption = localSelection?.selectedHistoryId
    ? options.find((o) => o.history_id === localSelection.selectedHistoryId)
    : null;

  const rawDisplayValue = localSelectedOption?.value ?? localSelection?.selectedValue ?? field.value;
  const displayValue = formatFieldValue(field.name, rawDisplayValue);

  // Determine which option is currently "active" (for highlighting in dropdown)
  // This is either the local selection or the currently confirmed value
  const activeHistoryId = localSelection?.selectedHistoryId ?? field.source?.history_id ?? null;

  return (
    <div className="relative flex-1 min-w-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between gap-2 px-2 py-1 rounded border text-sm text-left ${
          isConflict
            ? 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400'
            : 'bg-gray-700 border-gray-600 text-white'
        }`}
      >
        <span className="truncate">{displayValue ?? 'Choose value...'}</span>
        <svg
          className={`w-4 h-4 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />

          {/* Dropdown */}
          <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-20 overflow-hidden max-h-48 overflow-y-auto">
            {options.map((option) => {
              const isActive = option.history_id === activeHistoryId;
              return (
                <button
                  key={option.history_id}
                  onClick={() => {
                    onSelect(field.name, option);
                    setIsOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-left hover:bg-gray-700 transition-colors ${
                    isActive ? 'bg-gray-700' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-white">{formatFieldValue(field.name, option.value)}</span>
                    {isActive && !isConflict && (
                      <span className="text-xs text-blue-400">(current)</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">{formatDate(option.contributed_at)}</div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// =============================================================================
// Field Row Component
// =============================================================================

interface FieldRowProps {
  field: FieldDetail;
  localSelection: { selectedHistoryId: number | null; selectedValue: string | null } | undefined;
  onConflictSelect: (fieldName: string, option: ConflictOption) => void;
  onConfirm: (fieldName: string, historyId: number) => void;
  isConfirming: boolean;
  canEdit: boolean;
}

function FieldRow({ field, localSelection, onConflictSelect, onConfirm, isConfirming, canEdit }: FieldRowProps) {
  const isConflict = field.state === 'conflict';
  const hasMultipleOptions = (field.conflict_options?.length ?? 0) > 1;
  const hasLocalSelection = localSelection?.selectedHistoryId !== null;
  const hasValue = field.value !== null;

  // Determine if user has changed selection from the current confirmed value
  const hasNewSelection = hasLocalSelection &&
    localSelection?.selectedHistoryId !== field.source?.history_id;

  // Get state icon
  const getStateIcon = () => {
    if (isConflict) {
      return <span className="text-yellow-400 flex-shrink-0 w-4 text-center">!</span>;
    }
    if (field.state === 'confirmed') {
      return <span className="text-blue-400 flex-shrink-0 w-4 text-center">✓</span>;
    }
    if (hasValue) {
      return <span className="text-green-400 flex-shrink-0 w-4 text-center">✓</span>;
    }
    return <span className="text-gray-500 flex-shrink-0 w-4 text-center">○</span>;
  };

  const handleConfirm = () => {
    if (localSelection?.selectedHistoryId) {
      onConfirm(field.name, localSelection.selectedHistoryId);
    }
  };

  // Show dropdown if there are multiple options (conflict or confirmed with history)
  // But only if the order is editable (not created/processing/failed)
  const showDropdown = hasMultipleOptions && canEdit;

  return (
    <div
      className={`flex items-center gap-3 py-2 px-3 rounded ${
        isConflict
          ? 'bg-yellow-500/10'
          : !hasValue
            ? 'bg-gray-800/50'
            : 'bg-gray-800'
      }`}
    >
      {/* Status Icon */}
      {getStateIcon()}

      {/* Label */}
      <span className="text-sm text-gray-400 w-32 flex-shrink-0">{field.label}</span>

      {/* Value display - either dropdown (multiple options) or static text */}
      {showDropdown ? (
        <>
          <FieldDropdown
            field={field}
            localSelection={localSelection}
            onSelect={onConflictSelect}
            isConflict={isConflict}
          />
          {/* Confirm Button - shown when:
              - Unresolved conflict: must select to resolve
              - Confirmed field with new selection: user wants to change the value */}
          {canEdit && (isConflict || hasNewSelection) && (
            <button
              onClick={handleConfirm}
              disabled={!hasLocalSelection || isConfirming}
              className={`px-3 py-1 text-sm rounded font-medium transition-colors flex-shrink-0 ${
                hasLocalSelection && !isConfirming
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
              }`}
            >
              {isConfirming ? (
                <span className="inline-block w-4 h-4 border-2 border-gray-500 border-t-white rounded-full animate-spin" />
              ) : (
                'Confirm'
              )}
            </button>
          )}
        </>
      ) : (
        <span
          className={`text-sm truncate flex-1 ${hasValue ? 'text-white' : 'text-gray-600 italic'}`}
        >
          {formatFieldValue(field.name, field.value) ?? 'Missing'}
        </span>
      )}
    </div>
  );
}

// =============================================================================
// Source Card Component
// =============================================================================

interface SourceCardProps {
  source: ContributingSubRun;
  onViewSubRun: (subRunId: number) => void;
}

function SourceCard({ source, onViewSubRun }: SourceCardProps) {
  const isMockSource = source.sub_run_id === null;

  return (
    <div className="rounded-lg border border-gray-600 bg-gray-800 p-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-white break-words">{source.pdf_filename}</p>
        <p className="text-xs text-gray-400 mt-0.5 break-words">
          {source.source_type === 'email' ? (
            <>From: {source.source_identifier}</>
          ) : source.source_type === 'mock' ? (
            <span className="text-purple-400">{source.source_identifier}</span>
          ) : (
            <>{source.source_identifier}</>
          )}
        </p>
        {source.template_name && (
          <p className="text-xs text-gray-500 mt-0.5 break-words">
            Template: {source.template_name}
          </p>
        )}
        <p className="text-xs text-gray-500 mt-0.5">{formatDate(source.contributed_at)}</p>
      </div>

      <div className="mt-2 flex flex-wrap gap-1">
        {source.fields_contributed.map((fieldName) => (
          <span
            key={fieldName}
            className="text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-300"
          >
            {fieldName.replace(/_/g, ' ')}
          </span>
        ))}
      </div>

      {!isMockSource && (
        <button
          onClick={() => onViewSubRun(source.sub_run_id!)}
          className="mt-3 w-full text-xs py-1.5 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors"
        >
          View Details
        </button>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function PendingOrderDetailView({
  order,
  onBack,
  onConfirmField,
  onViewSubRun,
  confirmingFields = new Set(),
  onApprove,
  onReject,
  isApproving = false,
  isRejecting = false,
}: PendingOrderDetailViewProps) {
  // Track local conflict selections (before submitting to API)
  const [localSelections, setLocalSelections] = useState<LocalFieldState>({});

  const handleConflictSelect = (fieldName: string, option: ConflictOption) => {
    setLocalSelections((prev) => ({
      ...prev,
      [fieldName]: {
        selectedHistoryId: option.history_id,
        selectedValue: option.value,
      },
    }));
  };

  // Handle per-field confirm
  const handleFieldConfirm = (fieldName: string, historyId: number) => {
    onConfirmField(fieldName, historyId);
    // Clear local selection for this field after confirming
    setLocalSelections((prev) => {
      const newState = { ...prev };
      delete newState[fieldName];
      return newState;
    });
  };

  // Split fields into required and optional
  const requiredFields = useMemo(() => order.fields.filter((f) => f.required), [order.fields]);
  const optionalFields = useMemo(() => order.fields.filter((f) => !f.required), [order.fields]);

  // Calculate field counts
  const getEffectiveValue = (f: FieldDetail) => {
    if (f.value !== null) return true;
    return false;
  };

  const presentRequiredCount = requiredFields.filter(getEffectiveValue).length;
  const presentOptionalCount = optionalFields.filter(getEffectiveValue).length;

  // Count conflicts
  const conflictCount = order.fields.filter((f) => f.state === 'conflict').length;

  // Can edit only if order is incomplete or ready
  const canEdit = order.status === 'incomplete' || order.status === 'ready';

  // Get status display info
  const getStatusDisplay = () => {
    switch (order.status) {
      case 'incomplete':
        return { label: 'Incomplete', color: 'text-yellow-400', bg: 'bg-yellow-500/20 border-yellow-500/30' };
      case 'ready':
        return { label: 'Ready', color: 'text-green-400', bg: 'bg-green-500/20 border-green-500/30' };
      case 'processing':
        return { label: 'Processing', color: 'text-blue-400', bg: 'bg-blue-500/20 border-blue-500/30' };
      case 'created':
        return { label: 'Created', color: 'text-blue-400', bg: 'bg-blue-500/20 border-blue-500/30' };
      case 'failed':
        return { label: 'Failed', color: 'text-red-400', bg: 'bg-red-500/20 border-red-500/30' };
      case 'rejected':
        return { label: 'Rejected', color: 'text-gray-400', bg: 'bg-gray-500/20 border-gray-500/30' };
      default:
        return { label: order.status, color: 'text-gray-400', bg: 'bg-gray-500/20 border-gray-500/30' };
    }
  };

  // Can approve/reject only if order is ready
  const canApproveReject = order.status === 'ready';

  const statusDisplay = getStatusDisplay();

  return (
    <div className="h-full flex flex-col overflow-hidden bg-gray-900">
      {/* Header - Option C Layout */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-700">
        {/* Back Button Row */}
        <button
          onClick={onBack}
          className="text-gray-400 hover:text-white transition-colors flex items-center gap-2"
          title="Back to list"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back
        </button>

        {/* Order Info Row - Left: Info, Right: Status + Actions */}
        <div className="mt-4 flex items-start justify-between">
          {/* Left: HAWB and Customer */}
          <div>
            <span className="text-xs text-gray-500 uppercase tracking-wider">HAWB</span>
            <h1 className="text-2xl font-bold text-white font-mono">{order.hawb}</h1>
            <p className="text-sm text-gray-400 mt-1">
              {order.customer_name ?? `Customer ID: ${order.customer_id}`}
            </p>
          </div>

          {/* Right: Status Badge + Action Buttons */}
          <div className="flex items-start gap-4">
            {/* Status Badge */}
            <div className={`px-4 py-3 rounded-lg border ${statusDisplay.bg} text-right`}>
              <div className={`font-medium ${statusDisplay.color}`}>
                {statusDisplay.label}
              </div>
              {order.status === 'incomplete' && (
                <div className="text-xs text-gray-400 mt-1">
                  {presentRequiredCount}/{requiredFields.length} required fields
                  {conflictCount > 0 && ` · ${conflictCount} conflict${conflictCount > 1 ? 's' : ''}`}
                </div>
              )}
              {order.status === 'created' && order.htc_order_number && (
                <div className="text-xs text-gray-400 mt-1">
                  Order #{order.htc_order_number}
                </div>
              )}
            </div>

            {/* Approve/Reject Buttons - only when ready */}
            {canApproveReject && (
              <div className="flex gap-2">
                <button
                  onClick={onReject}
                  disabled={isRejecting || isApproving}
                  className="px-4 py-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isRejecting ? 'Rejecting...' : 'Reject'}
                </button>
                <button
                  onClick={onApprove}
                  disabled={isApproving || isRejecting}
                  className="px-4 py-2 rounded-lg border border-green-500/30 bg-green-500/10 text-green-400 hover:bg-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isApproving ? 'Creating...' : 'Approve'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left Column - Order Fields */}
        <div className="flex-1 overflow-auto p-6 border-r border-gray-700">
          {/* Required Fields */}
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Required ({presentRequiredCount}/{requiredFields.length})
            </h3>
            {requiredFields.map((field) => (
              <FieldRow
                key={field.name}
                field={field}
                localSelection={localSelections[field.name]}
                onConflictSelect={handleConflictSelect}
                onConfirm={handleFieldConfirm}
                isConfirming={confirmingFields.has(field.name)}
                canEdit={canEdit}
              />
            ))}
          </div>

          {/* Optional Fields */}
          <div className="mt-6 space-y-2">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Optional ({presentOptionalCount}/{optionalFields.length})
            </h3>
            {optionalFields.map((field) => (
              <FieldRow
                key={field.name}
                field={field}
                localSelection={localSelections[field.name]}
                onConflictSelect={handleConflictSelect}
                onConfirm={handleFieldConfirm}
                isConfirming={confirmingFields.has(field.name)}
                canEdit={canEdit}
              />
            ))}
          </div>
        </div>

        {/* Right Column - Data Sources */}
        <div className="w-[400px] flex-shrink-0 overflow-auto p-6 bg-gray-800/30 flex flex-col">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Sources ({order.contributing_sub_runs.length} PDFs)
          </h3>

          <div className="space-y-3 flex-1">
            {order.contributing_sub_runs.length === 0 ? (
              <p className="text-gray-500 text-sm italic">No sources yet</p>
            ) : (
              order.contributing_sub_runs.map((source, index) => (
                <SourceCard key={source.sub_run_id ?? `mock-${index}`} source={source} onViewSubRun={onViewSubRun} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
