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
  FieldState,
} from '../../types';

// =============================================================================
// Types
// =============================================================================

interface PendingOrderDetailViewProps {
  order: PendingOrderDetail;
  onBack: () => void;
  onResolveConflict: (fieldName: string, historyId: number) => void;
  onViewHistory: (hawb: string) => void;
  onViewSubRun: (subRunId: number) => void;
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

function getStatusColor(status: string): string {
  switch (status) {
    case 'incomplete':
      return 'text-yellow-400';
    case 'ready':
      return 'text-green-400';
    case 'created':
      return 'text-blue-400';
    default:
      return 'text-gray-400';
  }
}

function getStatusBgColor(status: string): string {
  switch (status) {
    case 'incomplete':
      return 'bg-yellow-500/20 border-yellow-500/30';
    case 'ready':
      return 'bg-green-500/20 border-green-500/30';
    case 'created':
      return 'bg-blue-500/20 border-blue-500/30';
    default:
      return 'bg-gray-500/20 border-gray-500/30';
  }
}

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

// =============================================================================
// Conflict Dropdown Component
// =============================================================================

interface ConflictDropdownProps {
  field: FieldDetail;
  localSelection: { selectedHistoryId: number | null; selectedValue: string | null } | undefined;
  onSelect: (fieldName: string, option: ConflictOption) => void;
}

function ConflictDropdown({ field, localSelection, onSelect }: ConflictDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const options = field.conflict_options ?? [];

  const selectedOption = localSelection?.selectedHistoryId
    ? options.find((o) => o.history_id === localSelection.selectedHistoryId)
    : null;

  const displayValue = selectedOption?.value ?? localSelection?.selectedValue;

  return (
    <div className="relative flex-1 min-w-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between gap-2 px-2 py-1 rounded border text-sm text-left ${
          displayValue
            ? 'bg-gray-700 border-gray-600 text-white'
            : 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400'
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
            {options.map((option) => (
              <button
                key={option.history_id}
                onClick={() => {
                  onSelect(field.name, option);
                  setIsOpen(false);
                }}
                className={`w-full px-3 py-2 text-left hover:bg-gray-700 transition-colors ${
                  localSelection?.selectedHistoryId === option.history_id ? 'bg-gray-700' : ''
                }`}
              >
                <div className="text-sm text-white">{option.value}</div>
                <div className="text-xs text-gray-500">{formatDate(option.contributed_at)}</div>
              </button>
            ))}
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
}

function FieldRow({ field, localSelection, onConflictSelect }: FieldRowProps) {
  const isConflict = field.state === 'conflict';
  const isResolved = isConflict && localSelection?.selectedHistoryId !== null;
  const hasValue = field.value !== null || isResolved;

  // Get display value
  let displayValue = field.value;
  if (isConflict && isResolved) {
    displayValue = localSelection?.selectedValue ?? null;
  }

  // Get state icon
  const getStateIcon = () => {
    if (isConflict && !isResolved) {
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

  return (
    <div
      className={`flex items-center justify-between py-2 px-3 rounded ${
        isConflict && !isResolved
          ? 'bg-yellow-500/10'
          : !hasValue
            ? 'bg-gray-800/50'
            : 'bg-gray-800'
      }`}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {/* Status Icon */}
        {getStateIcon()}

        {/* Label */}
        <span className="text-sm text-gray-400 w-32 flex-shrink-0">{field.label}</span>

        {/* Value or Conflict Dropdown */}
        {isConflict ? (
          <ConflictDropdown
            field={field}
            localSelection={localSelection}
            onSelect={onConflictSelect}
          />
        ) : (
          <span
            className={`text-sm truncate ${displayValue ? 'text-white' : 'text-gray-600 italic'}`}
          >
            {displayValue ?? 'Missing'}
          </span>
        )}
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
  return (
    <div className="rounded-lg border border-gray-600 bg-gray-800 p-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-white break-words">{source.pdf_filename}</p>
        <p className="text-xs text-gray-400 mt-0.5 break-words">
          {source.source_type === 'email' ? (
            <>From: {source.source_identifier}</>
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

      <button
        onClick={() => onViewSubRun(source.sub_run_id)}
        className="mt-3 w-full text-xs py-1.5 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors"
      >
        View Details
      </button>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function PendingOrderDetailView({
  order,
  onBack,
  onResolveConflict,
  onViewHistory,
  onViewSubRun,
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

    // Also trigger the API call
    onResolveConflict(fieldName, option.history_id);
  };

  // Split fields into required and optional
  const requiredFields = useMemo(() => order.fields.filter((f) => f.required), [order.fields]);
  const optionalFields = useMemo(() => order.fields.filter((f) => !f.required), [order.fields]);

  // Calculate field counts
  const getEffectiveValue = (f: FieldDetail) => {
    if (f.value !== null) return true;
    if (f.state === 'conflict' && localSelections[f.name]?.selectedHistoryId !== null) return true;
    return false;
  };

  const presentRequiredCount = requiredFields.filter(getEffectiveValue).length;
  const presentOptionalCount = optionalFields.filter(getEffectiveValue).length;
  const unresolvedConflicts = order.fields.filter(
    (f) => f.state === 'conflict' && !localSelections[f.name]?.selectedHistoryId
  );
  const missingRequired = requiredFields.filter((f) => !getEffectiveValue(f) && f.state !== 'conflict');

  // Build status message
  const getStatusMessage = () => {
    const parts: string[] = [];
    if (missingRequired.length > 0) {
      parts.push(`Missing: ${missingRequired.map((f) => f.label).join(', ')}`);
    }
    if (unresolvedConflicts.length > 0) {
      parts.push(
        `${unresolvedConflicts.length} conflict${unresolvedConflicts.length > 1 ? 's' : ''} to resolve`
      );
    }
    return parts.join(' · ');
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-gray-900">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-700">
        {/* Nav Row */}
        <div className="flex items-center justify-between">
          <button
            onClick={onBack}
            className="text-gray-400 hover:text-white transition-colors flex items-center gap-2"
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

          <button
            onClick={() => onViewHistory(order.hawb)}
            className="flex items-center gap-2 px-3 py-1.5 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 rounded transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            View History
          </button>
        </div>

        {/* Order Info + Status Row */}
        <div className="mt-3 flex items-center justify-between">
          {/* Left: Order Info */}
          <div className="flex items-center gap-6">
            <div>
              <span className="text-sm text-gray-500">HAWB</span>
              <h1 className="text-xl font-bold text-white font-mono">{order.hawb}</h1>
            </div>
            <div className="h-10 w-px bg-gray-700" />
            <div>
              <span className="text-sm text-gray-500">Customer</span>
              <p className="text-white">
                {order.customer_name ?? `ID: ${order.customer_id}`}
              </p>
            </div>
          </div>

          {/* Right: Status Badge */}
          <div className={`px-4 py-2 rounded-lg border ${getStatusBgColor(order.status)}`}>
            {order.status === 'incomplete' ? (
              <div className="flex items-center gap-3">
                <span className={`font-medium ${getStatusColor(order.status)}`}>
                  {presentRequiredCount}/{requiredFields.length} Fields
                </span>
                {getStatusMessage() && (
                  <span className="text-gray-400 text-sm">{getStatusMessage()}</span>
                )}
              </div>
            ) : order.status === 'ready' ? (
              <span className={`font-medium ${getStatusColor(order.status)}`}>
                Ready to Create
              </span>
            ) : (
              <div className="flex items-center gap-3">
                <span className={`font-medium ${getStatusColor(order.status)}`}>
                  Order #{order.htc_order_number}
                </span>
                <span className="text-gray-400 text-sm">Created</span>
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
              order.contributing_sub_runs.map((source) => (
                <SourceCard key={source.sub_run_id} source={source} onViewSubRun={onViewSubRun} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
