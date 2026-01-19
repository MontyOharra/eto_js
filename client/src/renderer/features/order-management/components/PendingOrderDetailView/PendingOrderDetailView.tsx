/**
 * PendingOrderDetailView Component
 *
 * Detailed view of a pending order with two-column layout:
 * - Left: Order fields with conflict resolution
 * - Right: Contributing data sources
 */

import { useState, useMemo } from 'react';
import type {
  PendingActionDetail,
  PendingActionFieldItem,
  ContributingSourceItem,
  OrderFieldDataType,
} from '../../types';
import { getStatusColorClasses } from '../../constants';
import { formatFieldValue as formatValue } from '../../utils/formatFieldValue';

// Derived types for internal component use
interface FieldDetail {
  name: string;
  label: string;
  data_type: OrderFieldDataType;
  value: unknown;
  state: 'set' | 'conflict' | 'confirmed';
  required: boolean;
  display_order: number;
  conflict_options: ConflictOption[] | null;
  source: { history_id: number } | null;
  sub_run_id: number | null; // For cross-highlighting with source cards
}

interface ConflictOption {
  history_id: number;
  value: unknown;
  contributed_at: string;
}

// Alias for source type used in component
type ContributingSubRun = ContributingSourceItem;

// =============================================================================
// Types
// =============================================================================

interface PendingOrderDetailViewProps {
  order: PendingActionDetail;
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
    selectedValue: unknown;
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

/**
 * Format a field value for display using the field's data type
 */
function formatFieldValue(value: unknown, dataType: OrderFieldDataType): string {
  return formatValue(value, dataType);
}

// =============================================================================
// Conflict Dropdown Component
// =============================================================================

interface FieldDropdownProps {
  field: FieldDetail;
  localSelection: { selectedHistoryId: number | null; selectedValue: unknown } | undefined;
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
  const displayValue = formatFieldValue(rawDisplayValue, field.data_type);

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
        <span className="truncate">{displayValue || 'Choose value...'}</span>
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
                    <span className="text-sm text-white">{formatFieldValue(option.value, field.data_type)}</span>
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
  localSelection: { selectedHistoryId: number | null; selectedValue: unknown } | undefined;
  onConflictSelect: (fieldName: string, option: ConflictOption) => void;
  onConfirm: (fieldName: string, historyId: number) => void;
  isConfirming: boolean;
  canEdit: boolean;
  isHighlighted: boolean;
  onHover: (fieldName: string | null) => void;
}

function FieldRow({ field, localSelection, onConflictSelect, onConfirm, isConfirming, canEdit, isHighlighted, onHover }: FieldRowProps) {
  const isConflict = field.state === 'conflict';
  const hasMultipleOptions = (field.conflict_options?.length ?? 0) > 1;
  const hasLocalSelection = localSelection?.selectedHistoryId !== null;
  const hasValue = field.value !== null && field.value !== undefined;

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
      className={`flex items-center gap-3 py-2 px-3 rounded transition-colors ${
        isHighlighted
          ? 'bg-blue-500/20 ring-1 ring-blue-500/50'
          : isConflict
            ? 'bg-yellow-500/10'
            : !hasValue
              ? 'bg-gray-800/50'
              : 'bg-gray-800'
      }`}
      onMouseEnter={() => onHover(field.name)}
      onMouseLeave={() => onHover(null)}
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
          className={`text-sm flex-1 min-w-0 ${hasValue ? 'text-white' : 'text-gray-600 italic'} ${
            'break-words'
          }`}
        >
          {(() => {
            const formatted = formatFieldValue(field.value, field.data_type);
            if (formatted) return formatted;
            // Distinguish between null/undefined (Missing) and empty string (Empty)
            return field.value === '' ? 'Empty' : 'Missing';
          })()}
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
  hoveredFieldName: string | null;
  onHover: (subRunId: number | null) => void;
  isHovered: boolean;
}

function SourceCard({ source, onViewSubRun, hoveredFieldName, onHover, isHovered }: SourceCardProps) {
  const isMockSource = source.sub_run_id === null;

  return (
    <div
      className={`rounded-lg border p-3 transition-colors ${
        isHovered
          ? 'border-blue-500/50 bg-blue-500/10 ring-1 ring-blue-500/50'
          : 'border-gray-600 bg-gray-800'
      }`}
      onMouseEnter={() => onHover(source.sub_run_id)}
      onMouseLeave={() => onHover(null)}
    >
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
        {source.fields_contributed.map((fieldName) => {
          const isHighlighted = hoveredFieldName === fieldName;
          return (
            <span
              key={fieldName}
              className={`text-xs px-1.5 py-0.5 rounded transition-colors ${
                isHighlighted
                  ? 'bg-blue-500/30 text-blue-300 ring-1 ring-blue-500/50'
                  : 'bg-gray-700 text-gray-300'
              }`}
            >
              {fieldName.replace(/_/g, ' ')}
            </span>
          );
        })}
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
  // Track hovered field name for cross-highlighting field tags in source cards
  const [hoveredFieldName, setHoveredFieldName] = useState<string | null>(null);
  // Track hovered source card for cross-highlighting field rows
  const [hoveredSubRunId, setHoveredSubRunId] = useState<number | null>(null);

  // Transform API fields to component format, showing ALL fields from metadata
  // (not just fields with values). This ensures empty/missing fields are visible.
  // For completed actions, use execution_result to show what was actually created.
  const transformedFields = useMemo((): FieldDetail[] => {
    const result: FieldDetail[] = [];
    const metadata = order.field_metadata ?? {};

    // For completed actions with execution_result, show the snapshot of what was created
    if (order.status === 'completed' && order.execution_result) {
      const execResult = order.execution_result;
      const newValues = execResult.new_values ?? {};

      // Show all fields that were set during creation
      for (const fieldName of execResult.fields_updated) {
        const fieldMeta = metadata[fieldName];
        if (!fieldMeta) continue;

        result.push({
          name: fieldName,
          label: fieldMeta.label,
          data_type: fieldMeta.data_type,
          value: newValues[fieldName] ?? null,
          state: 'set', // No conflicts for completed actions
          required: fieldMeta.required,
          display_order: fieldMeta.display_order,
          conflict_options: null,
          source: null,
          sub_run_id: null,
        });
      }

      // Sort by display_order
      result.sort((a, b) => a.display_order - b.display_order);
      return result;
    }

    // For non-completed actions, use the normal logic
    // Iterate over ALL fields defined in metadata (not just fields with values)
    for (const [fieldName, fieldMeta] of Object.entries(metadata)) {
      const label = fieldMeta.label;
      const required = fieldMeta.required;
      const displayOrder = fieldMeta.display_order;

      // Get field values if they exist (may be empty array or undefined)
      const fieldItems = order.fields[fieldName] ?? [];

      // Find the selected item (the current value)
      const selectedItem = fieldItems.find(item => item.is_selected);
      const hasMultipleValues = fieldItems.length > 1;
      const hasNoSelection = !selectedItem && fieldItems.length > 0;
      const hasNoValues = fieldItems.length === 0;

      // Determine field state
      let state: 'set' | 'conflict' | 'confirmed' = 'set';
      if (hasNoValues) {
        state = 'set'; // Empty field, no value yet
      } else if (hasNoSelection && hasMultipleValues) {
        state = 'conflict';
      } else if (selectedItem && hasMultipleValues) {
        state = 'confirmed';
      }

      // Build conflict options from all field items (keep values as objects)
      const conflictOptions: ConflictOption[] | null = hasMultipleValues
        ? fieldItems.map(item => ({
            history_id: item.id,
            value: item.value,
            contributed_at: order.updated_at,
          }))
        : null;

      // Determine the display value:
      // - If there's a selected item, use that
      // - If there's only one item (no selection needed), use that
      // - Otherwise null (conflict with no selection yet)
      let displayValue: unknown = null;
      let sourceRef: { history_id: number } | null = null;

      if (selectedItem) {
        displayValue = selectedItem.value;
        sourceRef = { history_id: selectedItem.id };
      } else if (fieldItems.length === 1) {
        // Single item - use it directly (no selection needed)
        const singleItem = fieldItems[0];
        displayValue = singleItem.value;
        sourceRef = { history_id: singleItem.id };
      }
      // else: multiple items with no selection = conflict, value stays null

      // Get sub_run_id for cross-highlighting (from selected or single item)
      const subRunId = selectedItem?.sub_run_id ?? (fieldItems.length === 1 ? fieldItems[0].sub_run_id : null);

      result.push({
        name: fieldName,
        label,
        data_type: fieldMeta.data_type,
        value: displayValue,
        state,
        required,
        display_order: displayOrder,
        conflict_options: conflictOptions,
        source: sourceRef,
        sub_run_id: subRunId,
      });
    }

    // Sort by display_order
    result.sort((a, b) => a.display_order - b.display_order);

    return result;
  }, [order.fields, order.field_metadata, order.updated_at, order.status, order.execution_result]);

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
  const requiredFields = useMemo(() => transformedFields.filter((f) => f.required), [transformedFields]);
  const optionalFields = useMemo(() => transformedFields.filter((f) => !f.required), [transformedFields]);

  // Calculate field counts
  const getEffectiveValue = (f: FieldDetail) => {
    return f.value !== null && f.value !== undefined;
  };

  const presentRequiredCount = requiredFields.filter(getEffectiveValue).length;
  const presentOptionalCount = optionalFields.filter(getEffectiveValue).length;

  // Count conflicts
  const conflictCount = transformedFields.filter((f) => f.state === 'conflict').length;

  // Can edit only if order is incomplete or ready
  const canEdit = order.status === 'incomplete' || order.status === 'ready' || order.status === 'conflict';

  // Get status display label
  const getStatusLabel = (status: string): string => {
    const labels: Record<string, string> = {
      incomplete: 'Incomplete',
      conflict: 'Conflict',
      ambiguous: 'Ambiguous',
      ready: 'Ready',
      processing: 'Processing',
      completed: 'Completed',
      created: 'Created',
      failed: 'Failed',
      rejected: 'Rejected',
    };
    return labels[status] ?? status;
  };

  // Can approve/reject only if order is ready
  const canApproveReject = order.status === 'ready';
  // Can retry only if order is failed
  const canRetry = order.status === 'failed';

  return (
    <div className="h-full flex flex-col overflow-hidden bg-gray-900">
      {/* Header */}
      <div className="flex-shrink-0 px-6 pt-4 pb-3 border-b border-gray-700">
        {/* Row 1: Back | Action Type | Status */}
        <div className="flex items-center justify-between">
          {/* Left: Back Button */}
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

          {/* Center: Action Type */}
          <div className="text-lg font-semibold text-white">
            New Order
          </div>

          {/* Right: Status Badge */}
          <div className={`px-3 py-1.5 rounded-lg border ${getStatusColorClasses(order.status)}`}>
            <span className="font-medium">
              {getStatusLabel(order.status)}
            </span>
          </div>
        </div>

        {/* Row 2: Customer/HAWB/Order# | Buttons */}
        <div className="mt-4 flex items-center justify-between">
          {/* Left: Customer, HAWB, HTC Order # - labels above values */}
          <div className="flex items-start gap-8">
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">Customer</span>
              <div className="text-xl text-white">
                {order.customer_name ?? `ID: ${order.customer_id}`}
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">HAWB</span>
              <div className="text-xl font-bold text-white font-mono">{order.hawb}</div>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">HTC Order #</span>
              <div className="text-xl text-white font-mono">{order.htc_order_number ?? '-'}</div>
            </div>
          </div>

          {/* Right: Buttons and extra info */}
          <div className="flex items-center gap-3">
            {/* Progress info for incomplete status */}
            {order.status === 'incomplete' && (
              <span className="text-xs text-gray-400">
                {presentRequiredCount}/{requiredFields.length} required
                {conflictCount > 0 && ` · ${conflictCount} conflict${conflictCount > 1 ? 's' : ''}`}
              </span>
            )}

            {/* Approve/Reject Buttons - only when ready */}
            {canApproveReject && (
              <>
                <button
                  onClick={onReject}
                  disabled={isRejecting || isApproving}
                  className="px-4 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  {isRejecting ? 'Rejecting...' : 'Reject'}
                </button>
                <button
                  onClick={onApprove}
                  disabled={isApproving || isRejecting}
                  className="px-4 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  {isApproving ? 'Creating...' : 'Approve'}
                </button>
              </>
            )}

            {/* Retry Button - only when failed */}
            {canRetry && (
              <button
                onClick={onApprove}
                disabled={isApproving}
                className="px-4 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
              >
                {isApproving ? 'Retrying...' : 'Retry'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left Column - Order Fields */}
        <div className="flex-1 min-w-0 overflow-auto p-6 border-r border-gray-700">
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
                isHighlighted={hoveredFieldName === field.name || (hoveredSubRunId !== null && field.sub_run_id === hoveredSubRunId)}
                onHover={setHoveredFieldName}
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
                isHighlighted={hoveredFieldName === field.name || (hoveredSubRunId !== null && field.sub_run_id === hoveredSubRunId)}
                onHover={setHoveredFieldName}
              />
            ))}
          </div>
        </div>

        {/* Right Column - Data Sources */}
        <div className="w-[400px] flex-shrink-0 overflow-auto p-6 bg-gray-800/30 flex flex-col">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Sources ({order.contributing_sources.length} PDFs)
          </h3>

          <div className="space-y-3 flex-1">
            {order.contributing_sources.length === 0 ? (
              <p className="text-gray-500 text-sm italic">No sources yet</p>
            ) : (
              order.contributing_sources.map((source, index) => (
                <SourceCard
                  key={source.sub_run_id ?? `mock-${index}`}
                  source={source}
                  onViewSubRun={onViewSubRun}
                  hoveredFieldName={hoveredFieldName}
                  onHover={setHoveredSubRunId}
                  isHovered={hoveredSubRunId === source.sub_run_id && source.sub_run_id !== null}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
