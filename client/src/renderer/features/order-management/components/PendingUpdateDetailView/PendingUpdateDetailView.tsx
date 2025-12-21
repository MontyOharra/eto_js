/**
 * PendingUpdateDetailView Component
 *
 * Detailed view of a pending update showing old -> new values:
 * - Left: Field changes with old -> new comparison
 * - Right: Contributing data sources
 *
 * Similar to PendingOrderDetailView but focused on updates to existing HTC orders.
 */

import { useState } from 'react';
import type {
  PendingUpdateDetail,
  PendingUpdateFieldDetail,
  ConflictOption,
  ContributingSubRun,
} from '../../types';

// =============================================================================
// Types
// =============================================================================

interface PendingUpdateDetailViewProps {
  update: PendingUpdateDetail;
  onBack: () => void;
  onApprove: (updateId: number) => void;
  onReject: (updateId: number) => void;
  onConfirmField: (fieldName: string, historyId: number) => void;
  onViewSubRun: (subRunId: number) => void;
  isApproving?: boolean;
  isRejecting?: boolean;
  confirmingFields?: Set<string>;
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
  field: PendingUpdateFieldDetail;
  localSelection: { selectedHistoryId: number | null; selectedValue: string | null } | undefined;
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

  const rawDisplayValue = localSelectedOption?.value ?? localSelection?.selectedValue ?? field.proposed_value;
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
// Field Row Component - Label | Old -> New (centered around arrow)
// =============================================================================

interface FieldRowProps {
  field: PendingUpdateFieldDetail;
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

  // Format current HTC value
  const currentValue = formatFieldValue(field.name, field.current_value);

  // Get the new value to display
  const newValue = localSelection?.selectedValue ?? field.proposed_value;
  const formattedNewValue = formatFieldValue(field.name, newValue);

  // Show dropdown if there are multiple options (conflict or confirmed with history)
  // But only if the update is editable (pending status)
  const showDropdown = hasMultipleOptions && canEdit;

  return (
    <div
      className={`py-2 px-3 rounded-lg border ${
        isConflict
          ? 'bg-yellow-500/5 border-yellow-500/30'
          : 'bg-gray-800/50 border-gray-700'
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Label - fixed width on left */}
        <div className="w-36 flex-shrink-0 flex items-center gap-2 pt-0.5">
          {isConflict && (
            <span className="text-yellow-400 text-sm">⚠</span>
          )}
          <span className="text-sm text-gray-400">{field.label}</span>
        </div>

        {/* Values section - flows naturally */}
        <div className="flex-1 min-w-0 flex flex-wrap items-start gap-x-3 gap-y-1">
          {/* Current Value - up to ~half width, then wraps */}
          <div className="max-w-[45%] flex items-center gap-2">
            <span className="text-sm text-gray-300 break-words">
              {currentValue ?? <span className="italic text-gray-500">Empty</span>}
            </span>
            {/* Arrow inline after current */}
            <svg className="w-4 h-4 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
              <span className="text-sm text-white break-words">
                {formattedNewValue ?? <span className="italic text-gray-500">N/A</span>}
              </span>
            )}
          </div>
        </div>
      </div>
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

export function PendingUpdateDetailView({
  update,
  onBack,
  onApprove,
  onReject,
  onConfirmField,
  onViewSubRun,
  isApproving = false,
  isRejecting = false,
  confirmingFields = new Set(),
}: PendingUpdateDetailViewProps) {
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

  const handleFieldConfirm = (fieldName: string, historyId: number) => {
    onConfirmField(fieldName, historyId);
    setLocalSelections((prev) => {
      const newState = { ...prev };
      delete newState[fieldName];
      return newState;
    });
  };

  // Filter to only fields with proposed changes
  const fieldsWithChanges = update.fields.filter((f) => f.state !== 'empty');
  const conflictCount = update.fields.filter((f) => f.state === 'conflict').length;

  // Can only edit pending updates
  const canEdit = update.status === 'pending';
  const hasConflicts = conflictCount > 0;

  // Get status display info
  const getStatusDisplay = () => {
    switch (update.status) {
      case 'pending':
        return { label: 'Pending Review', color: 'text-yellow-400', bg: 'bg-yellow-500/20 border-yellow-500/30' };
      case 'approved':
        return { label: 'Approved', color: 'text-green-400', bg: 'bg-green-500/20 border-green-500/30' };
      case 'rejected':
        return { label: 'Rejected', color: 'text-red-400', bg: 'bg-red-500/20 border-red-500/30' };
      default:
        return { label: update.status, color: 'text-gray-400', bg: 'bg-gray-500/20 border-gray-500/30' };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="h-full flex flex-col overflow-hidden bg-gray-900">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-700">
        {/* Top Row: Back button and main info */}
        <div className="flex items-start justify-between">
          {/* Left: Back + Order Info */}
          <div className="flex items-start gap-4">
            <button
              onClick={onBack}
              className="text-gray-400 hover:text-white transition-colors mt-1"
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
            </button>
            <div>
              <h1 className="text-xl font-bold text-white">
                <span className="font-mono">{update.hawb}</span>
                <span className="text-gray-400 font-normal mx-2">—</span>
                <span className="font-normal">{update.customer_name ?? `Customer ${update.customer_id}`}</span>
              </h1>
              <p className="text-sm text-gray-400 mt-0.5">
                HTC Order #{update.htc_order_number}
              </p>
            </div>
          </div>

          {/* Center: Review Update text */}
          <div className="text-center">
            <span className="text-lg font-medium text-gray-300">Review Update</span>
            <div className="text-xs text-gray-500 mt-0.5">
              {fieldsWithChanges.length} field{fieldsWithChanges.length !== 1 ? 's' : ''} to update
              {conflictCount > 0 && (
                <span className="text-yellow-400"> · {conflictCount} conflict{conflictCount !== 1 ? 's' : ''}</span>
              )}
            </div>
          </div>

          {/* Right: Status Badge + Action Buttons */}
          <div className="flex flex-col items-end gap-2">
            <div className={`px-3 py-1.5 rounded-lg border ${statusDisplay.bg}`}>
              <span className={`text-sm font-medium ${statusDisplay.color}`}>
                {statusDisplay.label}
              </span>
            </div>
            {canEdit && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onReject(update.id)}
                  disabled={isRejecting || isApproving}
                  className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRejecting ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 border-2 border-red-400/50 border-t-red-400 rounded-full animate-spin" />
                      Rejecting
                    </span>
                  ) : (
                    'Reject'
                  )}
                </button>
                <button
                  onClick={() => onApprove(update.id)}
                  disabled={isApproving || isRejecting || hasConflicts}
                  title={hasConflicts ? 'Resolve all conflicts before approving' : undefined}
                  className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isApproving ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                      Approving
                    </span>
                  ) : (
                    'Approve'
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left Column - Field Changes */}
        <div className="flex-1 overflow-auto p-6 border-r border-gray-700">
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
                  isConfirming={confirmingFields.has(field.name)}
                  canEdit={canEdit}
                />
              ))
            )}
          </div>
        </div>

        {/* Right Column - Data Sources */}
        <div className="w-[400px] flex-shrink-0 overflow-auto p-6 bg-gray-800/30 flex flex-col">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Sources ({update.contributing_sub_runs.length} PDFs)
          </h3>

          <div className="space-y-3 flex-1">
            {update.contributing_sub_runs.length === 0 ? (
              <p className="text-gray-500 text-sm italic">No sources yet</p>
            ) : (
              update.contributing_sub_runs.map((source, index) => (
                <SourceCard key={source.sub_run_id ?? `mock-${index}`} source={source} onViewSubRun={onViewSubRun} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
