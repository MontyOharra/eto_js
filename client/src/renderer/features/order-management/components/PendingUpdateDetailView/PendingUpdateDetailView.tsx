/**
 * PendingUpdateDetailView Component
 *
 * Detailed view of a pending update showing old -> new values:
 * - Left: Field changes with old -> new comparison
 * - Right: Contributing data sources
 *
 * Similar to PendingOrderDetailView but focused on updates to existing HTC orders.
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

// Internal field type for this component
interface PendingUpdateFieldDetail {
  name: string;
  label: string;
  data_type: OrderFieldDataType;
  current_value: unknown;
  proposed_value: unknown;
  state: 'empty' | 'set' | 'conflict' | 'confirmed';
  display_order: number;
  conflict_options: ConflictOption[] | null;
  source: { history_id: number } | null;
  sub_run_id: number | null; // For cross-highlighting with source cards
  is_approved_for_update: boolean; // Whether this field will be included in the update
  processing_status: 'success' | 'failed';
  processing_error: string | null;
}

interface ConflictOption {
  history_id: number;
  value: unknown;
  contributed_at: string;
  processing_status: 'success' | 'failed';
  processing_error: string | null;
}

// Alias for source type
type ContributingSubRun = ContributingSourceItem;

// =============================================================================
// Types
// =============================================================================

interface PendingUpdateDetailViewProps {
  update: PendingActionDetail;
  onBack: () => void;
  onApprove: (updateId: number) => void;
  onReject: (updateId: number) => void;
  onConfirmField: (fieldName: string, historyId: number) => void;
  onToggleFieldApproval: (fieldName: string, isApproved: boolean) => void;
  onViewSubRun: (subRunId: number) => void;
  isApproving?: boolean;
  isRejecting?: boolean;
  confirmingFields?: Set<string>;
  togglingApprovalFields?: Set<string>;
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
  field: PendingUpdateFieldDetail;
  localSelection: { selectedHistoryId: number | null; selectedValue: unknown } | undefined;
  onSelect: (fieldName: string, option: ConflictOption) => void;
  isConflict: boolean;
}

function FieldDropdown({ field, localSelection, onSelect, isConflict }: FieldDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const options = field.conflict_options ?? [];

  // Determine the display value:
  // 1. If user has made a local selection, use that
  // 2. Otherwise, use the field's proposed value (which is the confirmed/set value)
  const localSelectedOption = localSelection?.selectedHistoryId
    ? options.find((o) => o.history_id === localSelection.selectedHistoryId)
    : null;

  // Check if the currently displayed option is failed
  const isSelectedFailed = localSelectedOption?.processing_status === 'failed' || field.processing_status === 'failed';
  const selectedError = localSelectedOption?.processing_error ?? field.processing_error;

  const rawDisplayValue = localSelectedOption?.value ?? localSelection?.selectedValue ?? field.proposed_value;
  const displayValue = isSelectedFailed && selectedError
    ? `Error: ${selectedError}`
    : formatFieldValue(rawDisplayValue, field.data_type);

  // Determine which option is currently "active" (for highlighting in dropdown)
  // This is either the local selection or the currently confirmed value
  const activeHistoryId = localSelection?.selectedHistoryId ?? field.source?.history_id ?? null;

  return (
    <div className="relative flex-1 min-w-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between gap-2 px-2 py-1 rounded border text-sm text-left ${
          isSelectedFailed
            ? 'bg-red-500/10 border-red-500/50 text-red-400'
            : isConflict
              ? 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400'
              : 'bg-gray-700 border-gray-600 text-white'
        }`}
      >
        <span className={`truncate ${isSelectedFailed ? 'italic' : ''}`}>{displayValue || 'Choose value...'}</span>
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
              const isOptionFailed = option.processing_status === 'failed';
              const optionDisplayValue = isOptionFailed && option.processing_error
                ? `Error: ${option.processing_error}`
                : formatFieldValue(option.value, field.data_type);
              return (
                <button
                  key={option.history_id}
                  onClick={() => {
                    onSelect(field.name, option);
                    setIsOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-left hover:bg-gray-700 transition-colors ${
                    isActive ? 'bg-gray-700' : ''
                  } ${isOptionFailed ? 'border-l-2 border-red-500' : ''}`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${isOptionFailed ? 'text-red-400 italic' : 'text-white'}`}>
                      {optionDisplayValue}
                    </span>
                    {isActive && !isConflict && (
                      <span className="text-xs text-blue-400">(current)</span>
                    )}
                    {isOptionFailed && (
                      <span className="text-xs text-red-400">(failed)</span>
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
// Field Row Component - Label | Old -> New (centered around arrow)
// =============================================================================

interface FieldRowProps {
  field: PendingUpdateFieldDetail;
  localSelection: { selectedHistoryId: number | null; selectedValue: unknown } | undefined;
  onConflictSelect: (fieldName: string, option: ConflictOption) => void;
  onConfirm: (fieldName: string, historyId: number) => void;
  onToggleApproval: (fieldName: string, isApproved: boolean) => void;
  isConfirming: boolean;
  isTogglingApproval: boolean;
  canEdit: boolean;
  isHighlighted: boolean;
  onHover: (fieldName: string | null) => void;
}

function FieldRow({ field, localSelection, onConflictSelect, onConfirm, onToggleApproval, isConfirming, isTogglingApproval, canEdit, isHighlighted, onHover }: FieldRowProps) {
  const isConflict = field.state === 'conflict';
  const isFailed = field.processing_status === 'failed';
  const hasMultipleOptions = (field.conflict_options?.length ?? 0) > 1;
  const hasLocalSelection = localSelection?.selectedHistoryId !== null;
  const isApproved = field.is_approved_for_update;

  // Empty state - no proposed change for this field
  if (field.state === 'empty') {
    return null; // Don't show fields with no proposed changes
  }

  // Determine if user has changed selection from the current confirmed value
  const hasNewSelection = hasLocalSelection &&
    localSelection?.selectedHistoryId !== field.source?.history_id;

  const handleConfirm = () => {
    if (localSelection?.selectedHistoryId) {
      onConfirm(field.name, localSelection.selectedHistoryId);
    }
  };

  const handleToggleApproval = () => {
    onToggleApproval(field.name, !isApproved);
  };

  // Format current HTC value
  const currentValue = formatFieldValue(field.current_value, field.data_type);

  // Get the new value to display - for failed fields, show error message
  const newValue = localSelection?.selectedValue ?? field.proposed_value;
  const formattedNewValue = isFailed && field.processing_error
    ? `Error: ${field.processing_error}`
    : formatFieldValue(newValue, field.data_type);

  // Show dropdown if there are multiple options (conflict or confirmed with history)
  // But only if the update is editable (pending status)
  const showDropdown = hasMultipleOptions && canEdit;

  return (
    <div className="flex items-stretch gap-2">
      {/* Main Row Content */}
      <div
        className={`flex-1 py-2 px-3 rounded-lg border transition-colors ${
          !isApproved
            ? 'bg-gray-800/30 border-gray-700/50 opacity-60'
            : isHighlighted
              ? 'bg-blue-500/20 border-blue-500/50 ring-1 ring-blue-500/50'
              : isFailed
                ? 'bg-red-500/5 border-red-500/30'
                : isConflict
                  ? 'bg-yellow-500/5 border-yellow-500/30'
                  : 'bg-gray-800/50 border-gray-700'
        }`}
        onMouseEnter={() => onHover(field.name)}
        onMouseLeave={() => onHover(null)}
      >
        <div className="flex items-start gap-3">
          {/* Label - fixed width on left */}
          <div className="w-32 flex-shrink-0 flex items-center gap-2 pt-0.5">
            {isFailed && (
              <span className="text-red-400 text-sm">✕</span>
            )}
            {isConflict && !isFailed && (
              <span className="text-yellow-400 text-sm">⚠</span>
            )}
            <span className={`text-sm ${isApproved ? 'text-gray-400' : 'text-gray-500 line-through'}`}>{field.label}</span>
          </div>

          {/* Values section - flows naturally */}
          <div className="flex-1 min-w-0 flex flex-wrap items-start gap-x-3 gap-y-1">
            {/* Current Value - up to ~half width, then wraps */}
            <div className="max-w-[40%] flex items-start gap-2">
              <span className={`text-sm break-words ${isApproved ? 'text-gray-300' : 'text-gray-500'}`}>
                {currentValue || <span className="italic text-gray-500">Empty</span>}
              </span>
              {/* Arrow inline after current */}
              <svg className={`w-4 h-4 flex-shrink-0 ${isApproved ? 'text-gray-500' : 'text-gray-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </div>

            {/* New Value */}
            <div className="flex-1 min-w-0 flex items-center gap-2">
              {showDropdown ? (
                <>
                  <FieldDropdown
                    field={field}
                    localSelection={localSelection}
                    onSelect={onConflictSelect}
                    isConflict={isConflict}
                  />
                  {/* Confirm Button */}
                  {(isConflict || hasNewSelection) && (
                    <button
                      onClick={handleConfirm}
                      disabled={!hasLocalSelection || isConfirming}
                      className={`flex-shrink-0 px-3 py-1 text-sm rounded font-medium transition-colors ${
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
                <span className={`text-sm break-words ${
                  isFailed
                    ? 'text-red-400 italic'
                    : isApproved
                      ? 'text-white'
                      : 'text-gray-500'
                }`}>
                  {formattedNewValue || <span className="italic text-gray-500">Empty</span>}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Include/Exclude Toggle Button - separate from the row */}
      {canEdit && (
        <button
          onClick={handleToggleApproval}
          disabled={isTogglingApproval}
          className={`flex-shrink-0 w-20 rounded-lg border text-sm font-medium transition-colors flex items-center justify-center ${
            isTogglingApproval
              ? 'bg-gray-700 border-gray-600 text-gray-500 cursor-not-allowed'
              : isApproved
                ? 'bg-gray-700 border-gray-600 hover:bg-gray-600 text-gray-300'
                : 'bg-green-700 border-green-600 hover:bg-green-600 text-white'
          }`}
          title={isApproved ? 'Exclude this field from update' : 'Include this field in update'}
        >
          {isTogglingApproval ? (
            <span className="inline-block w-4 h-4 border-2 border-gray-500 border-t-white rounded-full animate-spin" />
          ) : isApproved ? (
            'Exclude'
          ) : (
            'Include'
          )}
        </button>
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

export function PendingUpdateDetailView({
  update,
  onBack,
  onApprove,
  onReject,
  onConfirmField,
  onToggleFieldApproval,
  onViewSubRun,
  isApproving = false,
  isRejecting = false,
  confirmingFields = new Set(),
  togglingApprovalFields = new Set(),
}: PendingUpdateDetailViewProps) {
  const [localSelections, setLocalSelections] = useState<LocalFieldState>({});
  // Track hovered field name for cross-highlighting field tags in source cards
  const [hoveredFieldName, setHoveredFieldName] = useState<string | null>(null);
  // Track hovered source card for cross-highlighting field rows
  const [hoveredSubRunId, setHoveredSubRunId] = useState<number | null>(null);

  // Transform API fields to internal format, showing ALL fields from metadata
  // (not just fields with values). This ensures empty/missing fields are visible.
  // For completed actions, use execution_result to show what actually changed.
  const transformedFields = useMemo((): PendingUpdateFieldDetail[] => {
    const result: PendingUpdateFieldDetail[] = [];
    const metadata = update.field_metadata ?? {};

    // For completed actions with execution_result, show the snapshot of what changed
    if (update.status === 'completed' && update.execution_result) {
      const execResult = update.execution_result;
      const oldValues = execResult.old_values ?? {};
      const newValues = execResult.new_values ?? {};

      // Only show fields that were actually updated
      for (const fieldName of execResult.fields_updated) {
        const fieldMeta = metadata[fieldName];
        if (!fieldMeta) continue;

        result.push({
          name: fieldName,
          label: fieldMeta.label,
          data_type: fieldMeta.data_type,
          current_value: oldValues[fieldName] ?? null,
          proposed_value: newValues[fieldName] ?? null,
          state: 'set', // No conflicts for completed actions
          display_order: fieldMeta.display_order,
          conflict_options: null,
          source: null,
          sub_run_id: null,
          is_approved_for_update: true,
          processing_status: 'success', // Completed actions are always successful
          processing_error: null,
        });
      }

      // Sort by display_order
      result.sort((a, b) => a.display_order - b.display_order);
      return result;
    }

    // For non-completed actions, use the normal logic
    const currentHtcValues = update.current_htc_values ?? {};

    // Iterate over ALL fields defined in metadata (not just fields with values)
    for (const [fieldName, fieldMeta] of Object.entries(metadata)) {
      const label = fieldMeta.label;
      const displayOrder = fieldMeta.display_order;
      const dataType = fieldMeta.data_type;

      // Get field values if they exist (may be empty array or undefined)
      const fieldItems = update.fields[fieldName] ?? [];

      const selectedItem = fieldItems.find(item => item.is_selected);
      const hasMultipleValues = fieldItems.length > 1;
      const hasNoSelection = !selectedItem && fieldItems.length > 0;
      const hasNoValues = fieldItems.length === 0;

      // Get current HTC value for comparison (keep as object)
      const currentValue = currentHtcValues[fieldName] ?? null;

      // Determine state
      let state: 'empty' | 'set' | 'conflict' | 'confirmed' = 'set';
      if (hasNoValues) {
        state = 'empty'; // No proposed value for this field
      } else if (hasNoSelection && hasMultipleValues) {
        state = 'conflict';
      } else if (selectedItem && hasMultipleValues) {
        state = 'confirmed';
      }

      // Determine the proposed value (keep as object):
      // - If there's a selected item, use that
      // - If there's only one item (no selection needed), use that
      // - Otherwise null (conflict with no selection yet)
      let proposedValue: unknown = null;
      let sourceRef: { history_id: number } | null = null;

      if (selectedItem) {
        proposedValue = selectedItem.value;
        sourceRef = { history_id: selectedItem.id };
      } else if (fieldItems.length === 1) {
        // Single item - use it directly (no selection needed)
        const singleItem = fieldItems[0];
        proposedValue = singleItem.value;
        sourceRef = { history_id: singleItem.id };
      }
      // else: multiple items with no selection = conflict, value stays null

      // Build conflict options (keep values as objects)
      const conflictOptions: ConflictOption[] | null = hasMultipleValues
        ? fieldItems.map(item => ({
            history_id: item.id,
            value: item.value,
            contributed_at: update.updated_at,
            processing_status: item.processing_status,
            processing_error: item.processing_error,
          }))
        : null;

      // Get sub_run_id for cross-highlighting (from selected or single item)
      const subRunId = selectedItem?.sub_run_id ?? (fieldItems.length === 1 ? fieldItems[0].sub_run_id : null);

      // Get is_approved_for_update - all values for a field share the same approval status
      // Default to true if no field items exist
      const isApprovedForUpdate = fieldItems.length > 0 ? fieldItems[0].is_approved_for_update : true;

      // Get processing status from selected or single item
      const processingStatus = selectedItem?.processing_status ?? (fieldItems.length === 1 ? fieldItems[0].processing_status : 'success');
      const processingError = selectedItem?.processing_error ?? (fieldItems.length === 1 ? fieldItems[0].processing_error : null);

      result.push({
        name: fieldName,
        label,
        data_type: dataType,
        current_value: currentValue,
        proposed_value: proposedValue,
        state,
        display_order: displayOrder,
        conflict_options: conflictOptions,
        source: sourceRef,
        sub_run_id: subRunId,
        is_approved_for_update: isApprovedForUpdate,
        processing_status: processingStatus ?? 'success',
        processing_error: processingError ?? null,
      });
    }

    // Sort by display_order
    result.sort((a, b) => a.display_order - b.display_order);

    return result;
  }, [update.fields, update.field_metadata, update.current_htc_values, update.updated_at, update.status, update.execution_result]);

  const handleConflictSelect = (fieldName: string, option: ConflictOption) => {
    setLocalSelections((prev) => ({
      ...prev,
      [fieldName]: {
        selectedHistoryId: option.history_id,
        selectedValue: option.value,
      },
    }));
  };

  const handleFieldConfirm = (fieldName: string, historyId: number) => {
    onConfirmField(fieldName, historyId);
    setLocalSelections((prev) => {
      const newState = { ...prev };
      delete newState[fieldName];
      return newState;
    });
  };

  // Filter to only fields with proposed changes
  const fieldsWithChanges = transformedFields.filter((f) => f.state !== 'empty');
  const conflictCount = transformedFields.filter((f) => f.state === 'conflict').length;

  // Can edit if status allows changes (not completed/rejected/processing)
  const canEdit = update.status === 'incomplete' || update.status === 'ready' || update.status === 'conflict';
  // Can retry only if update is failed
  const canRetry = update.status === 'failed';
  const hasConflicts = conflictCount > 0;

  // Get status display label
  const getStatusLabel = (status: string): string => {
    const labels: Record<string, string> = {
      incomplete: 'Incomplete',
      conflict: 'Conflict',
      ambiguous: 'Ambiguous',
      ready: 'Ready',
      processing: 'Processing',
      completed: 'Completed',
      pending: 'Pending Review',
      approved: 'Approved',
      failed: 'Failed',
      rejected: 'Rejected',
    };
    return labels[status] ?? status;
  };

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
            Order Update
          </div>

          {/* Right: Status Badge */}
          <div className={`px-3 py-1.5 rounded-lg border ${getStatusColorClasses(update.status)}`}>
            <span className="font-medium">
              {getStatusLabel(update.status)}
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
                {update.customer_name ?? `ID: ${update.customer_id}`}
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">HAWB</span>
              <div className="text-xl font-bold text-white font-mono">{update.hawb}</div>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wider">HTC Order #</span>
              <div className="text-xl text-white font-mono">{update.htc_order_number ?? '-'}</div>
            </div>
          </div>

          {/* Right: Buttons and extra info */}
          <div className="flex items-center gap-3">
            {/* Changes info */}
            <span className="text-xs text-gray-400">
              {fieldsWithChanges.length} field{fieldsWithChanges.length !== 1 ? 's' : ''}
              {conflictCount > 0 && ` · ${conflictCount} conflict${conflictCount > 1 ? 's' : ''}`}
            </span>

            {/* Approve/Reject Buttons - only when editable */}
            {canEdit && (
              <>
                <button
                  onClick={() => onReject(update.id)}
                  disabled={isRejecting || isApproving}
                  className="px-4 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  {isRejecting ? 'Rejecting...' : 'Reject'}
                </button>
                <button
                  onClick={() => onApprove(update.id)}
                  disabled={isApproving || isRejecting || hasConflicts}
                  title={hasConflicts ? 'Resolve all conflicts before approving' : undefined}
                  className="px-4 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  {isApproving ? 'Approving...' : 'Approve'}
                </button>
              </>
            )}

            {/* Retry Button - only when failed */}
            {canRetry && (
              <button
                onClick={() => onApprove(update.id)}
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
        {/* Left Column - Field Changes */}
        <div className="flex-1 min-w-0 overflow-auto p-6 border-r border-gray-700">
          {/* Column Headers Row */}
          <div className="flex items-center py-2 px-3 mb-3 border-b border-gray-700">
            <div className="w-36 flex-shrink-0">
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Field</span>
            </div>
            <div className="flex-1 min-w-0 flex gap-3">
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Current</span>
              <span className="text-xs text-gray-600">→</span>
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">New</span>
            </div>
          </div>

          <div className="space-y-2">
            {fieldsWithChanges.length === 0 ? (
              <p className="text-gray-500 text-sm italic">No field changes proposed</p>
            ) : (
              fieldsWithChanges.map((field) => (
                <FieldRow
                  key={field.name}
                  field={field}
                  localSelection={localSelections[field.name]}
                  onConflictSelect={handleConflictSelect}
                  onConfirm={handleFieldConfirm}
                  onToggleApproval={onToggleFieldApproval}
                  isConfirming={confirmingFields.has(field.name)}
                  isTogglingApproval={togglingApprovalFields.has(field.name)}
                  canEdit={canEdit}
                  isHighlighted={hoveredFieldName === field.name || (hoveredSubRunId !== null && field.sub_run_id === hoveredSubRunId)}
                  onHover={setHoveredFieldName}
                />
              ))
            )}
          </div>
        </div>

        {/* Right Column - Data Sources */}
        <div className="w-[400px] flex-shrink-0 overflow-auto p-6 bg-gray-800/30 flex flex-col">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Sources ({update.contributing_sources.length} PDFs)
          </h3>

          <div className="space-y-3 flex-1">
            {update.contributing_sources.length === 0 ? (
              <p className="text-gray-500 text-sm italic">No sources yet</p>
            ) : (
              update.contributing_sources.map((source, index) => (
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
