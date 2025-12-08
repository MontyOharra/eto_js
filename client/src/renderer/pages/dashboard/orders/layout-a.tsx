import { createFileRoute, Link } from '@tanstack/react-router';
import { useState } from 'react';

export const Route = createFileRoute('/dashboard/orders/layout-a')({
  component: LayoutAPage,
});

// =============================================================================
// Types
// =============================================================================

interface ConflictOption {
  value: string;
  pdfFilename: string;
  emailSubject: string;
}

interface FieldData {
  name: string;
  label: string;
  value: string | null;
  required: boolean;
  source: { pdfFilename: string; emailSubject: string } | null;
  conflict?: {
    options: ConflictOption[];
    selectedIndex: number | null; // null = not yet chosen
  };
}

// =============================================================================
// Mock Data
// =============================================================================

const mockOrder = {
  id: 1,
  hawb: '123-45678901',
  customer_name: 'ABC Logistics',
  customer_id: 42,
  status: 'incomplete' as const,
  htc_order_number: null,
  created_at: '2025-12-05T14:30:00Z',
  updated_at: '2025-12-05T15:45:00Z',
  htc_created_at: null,
};

const initialFields: FieldData[] = [
  {
    name: 'hawb',
    label: 'HAWB',
    value: '123-45678901',
    required: true,
    source: { pdfFilename: 'routing_form.pdf', emailSubject: 'SOS Routing - Order 12345' },
  },
  {
    name: 'mawb',
    label: 'MAWB',
    value: '999-12345678',
    required: false,
    source: { pdfFilename: 'mawb_form.pdf', emailSubject: 'MAWB Info - Shipment ABC' },
  },
  {
    name: 'pickup_address',
    label: 'Pickup Address',
    value: '123 Main St, Suite 400, Chicago, IL 60601',
    required: true,
    source: { pdfFilename: 'routing_form.pdf', emailSubject: 'SOS Routing - Order 12345' },
  },
  {
    name: 'pickup_time_start',
    label: 'Pickup Start',
    value: null, // null because conflict not resolved
    required: true,
    source: null,
    conflict: {
      options: [
        { value: '08:00 AM', pdfFilename: 'routing_form.pdf', emailSubject: 'SOS Routing - Order 12345' },
        { value: '09:00 AM', pdfFilename: 'updated_routing.pdf', emailSubject: 'Updated SOS Routing' },
      ],
      selectedIndex: null,
    },
  },
  {
    name: 'pickup_time_end',
    label: 'Pickup End',
    value: '10:00 AM',
    required: true,
    source: { pdfFilename: 'routing_form.pdf', emailSubject: 'SOS Routing - Order 12345' },
  },
  {
    name: 'delivery_address',
    label: 'Delivery Address',
    value: null,
    required: true,
    source: null,
  },
  {
    name: 'delivery_time_start',
    label: 'Delivery Start',
    value: null,
    required: true,
    source: null,
  },
  {
    name: 'delivery_time_end',
    label: 'Delivery End',
    value: null,
    required: true,
    source: null,
  },
  {
    name: 'pickup_notes',
    label: 'Pickup Notes',
    value: 'Call ahead 30 min before arrival',
    required: false,
    source: { pdfFilename: 'routing_form.pdf', emailSubject: 'SOS Routing - Order 12345' },
  },
  {
    name: 'delivery_notes',
    label: 'Delivery Notes',
    value: null,
    required: false,
    source: null,
  },
  {
    name: 'pieces',
    label: 'Pieces',
    value: '5',
    required: false,
    source: { pdfFilename: 'mawb_form.pdf', emailSubject: 'MAWB Info - Shipment ABC' },
  },
  {
    name: 'weight',
    label: 'Weight',
    value: '125 lbs',
    required: false,
    source: { pdfFilename: 'mawb_form.pdf', emailSubject: 'MAWB Info - Shipment ABC' },
  },
];

const mockDataSources = [
  {
    pdfFilename: 'routing_form.pdf',
    emailSubject: 'SOS Routing - Order 12345',
    fieldsContributed: ['hawb', 'pickup_address', 'pickup_time_start', 'pickup_time_end', 'pickup_notes'],
  },
  {
    pdfFilename: 'mawb_form.pdf',
    emailSubject: 'MAWB Info - Shipment ABC',
    fieldsContributed: ['mawb', 'pieces', 'weight'],
  },
  {
    pdfFilename: 'updated_routing.pdf',
    emailSubject: 'Updated SOS Routing',
    fieldsContributed: ['pickup_time_start'],
  },
];

// =============================================================================
// Helper Functions
// =============================================================================

function getStatusColor(status: string): string {
  switch (status) {
    case 'incomplete': return 'text-yellow-400';
    case 'ready': return 'text-green-400';
    case 'created': return 'text-blue-400';
    default: return 'text-gray-400';
  }
}

function getStatusBgColor(status: string): string {
  switch (status) {
    case 'incomplete': return 'bg-yellow-500/20 border-yellow-500/30';
    case 'ready': return 'bg-green-500/20 border-green-500/30';
    case 'created': return 'bg-blue-500/20 border-blue-500/30';
    default: return 'bg-gray-500/20 border-gray-500/30';
  }
}

// =============================================================================
// Conflict Dropdown Component
// =============================================================================

interface ConflictDropdownProps {
  field: FieldData;
  onSelect: (fieldName: string, optionIndex: number) => void;
}

function ConflictDropdown({ field, onSelect }: ConflictDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const conflict = field.conflict!;
  const selectedOption = conflict.selectedIndex !== null ? conflict.options[conflict.selectedIndex] : null;

  return (
    <div className="relative flex-1 min-w-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between gap-2 px-2 py-1 rounded border text-sm text-left ${
          selectedOption
            ? 'bg-gray-700 border-gray-600 text-white'
            : 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400'
        }`}
      >
        <span className="truncate">
          {selectedOption ? selectedOption.value : 'Choose value...'}
        </span>
        <svg className={`w-4 h-4 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />

          {/* Dropdown */}
          <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-20 overflow-hidden">
            {conflict.options.map((option, idx) => (
              <button
                key={idx}
                onClick={() => {
                  onSelect(field.name, idx);
                  setIsOpen(false);
                }}
                className={`w-full px-3 py-2 text-left hover:bg-gray-700 transition-colors ${
                  conflict.selectedIndex === idx ? 'bg-gray-700' : ''
                }`}
              >
                <div className="text-sm text-white">{option.value}</div>
                <div className="text-xs text-gray-500">{option.pdfFilename}</div>
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
  field: FieldData;
  onConflictSelect: (fieldName: string, optionIndex: number) => void;
}

function FieldRow({ field, onConflictSelect }: FieldRowProps) {
  const hasConflict = !!field.conflict;
  const isResolved = hasConflict && field.conflict!.selectedIndex !== null;
  const hasValue = field.value !== null || isResolved;

  // Get display value and source
  let displayValue = field.value;
  let displaySource = field.source?.pdfFilename;

  if (hasConflict && isResolved) {
    const selected = field.conflict!.options[field.conflict!.selectedIndex!];
    displayValue = selected.value;
    displaySource = selected.pdfFilename;
  }

  return (
    <div
      className={`flex items-center justify-between py-2 px-3 rounded ${
        hasConflict && !isResolved
          ? 'bg-yellow-500/10'
          : !hasValue
          ? 'bg-gray-800/50'
          : 'bg-gray-800'
      }`}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {/* Status Icon */}
        {hasConflict && !isResolved ? (
          <span className="text-yellow-400 flex-shrink-0">!</span>
        ) : hasValue ? (
          <span className="text-green-400 flex-shrink-0">✓</span>
        ) : (
          <span className="text-gray-500 flex-shrink-0">○</span>
        )}

        {/* Label */}
        <span className="text-sm text-gray-400 w-28 flex-shrink-0">{field.label}</span>

        {/* Value or Conflict Dropdown */}
        {hasConflict ? (
          <ConflictDropdown field={field} onSelect={onConflictSelect} />
        ) : (
          <span className={`text-sm truncate ${displayValue ? 'text-white' : 'text-gray-600 italic'}`}>
            {displayValue ?? 'Missing'}
          </span>
        )}
      </div>

      {/* Source (PDF name only) - only show if not a conflict dropdown */}
      {!hasConflict && displaySource && (
        <span className="text-xs text-gray-500 flex-shrink-0 ml-4">
          {displaySource}
        </span>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

function LayoutAPage() {
  const [fields, setFields] = useState<FieldData[]>(initialFields);

  const handleConflictSelect = (fieldName: string, optionIndex: number) => {
    setFields(prev => prev.map(f => {
      if (f.name === fieldName && f.conflict) {
        const selected = f.conflict.options[optionIndex];
        return {
          ...f,
          value: selected.value,
          source: { pdfFilename: selected.pdfFilename, emailSubject: selected.emailSubject },
          conflict: { ...f.conflict, selectedIndex: optionIndex },
        };
      }
      return f;
    }));
  };

  const handleViewAllPdfs = () => {
    // This would open a modal or navigate to a unified PDF viewer
    console.log('View all PDFs:', mockDataSources.map(s => s.pdfFilename));
    alert('This would open a unified view of all PDFs:\n\n' + mockDataSources.map(s => `• ${s.pdfFilename}`).join('\n'));
  };

  const requiredFields = fields.filter(f => f.required);
  const optionalFields = fields.filter(f => !f.required);

  // Count fields that have values OR have resolved conflicts
  const getEffectiveValue = (f: FieldData) => {
    if (f.value !== null) return true;
    if (f.conflict && f.conflict.selectedIndex !== null) return true;
    return false;
  };

  const presentRequiredCount = requiredFields.filter(getEffectiveValue).length;
  const unresolvedConflicts = fields.filter(f => f.conflict && f.conflict.selectedIndex === null);
  const missingRequired = requiredFields.filter(f => !getEffectiveValue(f) && !f.conflict);

  // Build status message
  const getStatusMessage = () => {
    const parts: string[] = [];
    if (missingRequired.length > 0) {
      parts.push(`Missing: ${missingRequired.map(f => f.label).join(', ')}`);
    }
    if (unresolvedConflicts.length > 0) {
      parts.push(`${unresolvedConflicts.length} conflict${unresolvedConflicts.length > 1 ? 's' : ''} to resolve`);
    }
    return parts.join(' · ');
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-gray-900">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-700">
        {/* Nav Row */}
        <div className="flex items-center">
          <Link
            to="/dashboard/orders"
            className="text-gray-400 hover:text-white transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </Link>
        </div>

        {/* Order Info + Status Row */}
        <div className="mt-3 flex items-center justify-between">
          {/* Left: Order Info */}
          <div className="flex items-center gap-6">
            <div>
              <span className="text-sm text-gray-500">HAWB</span>
              <h1 className="text-xl font-bold text-white">{mockOrder.hawb}</h1>
            </div>
            <div className="h-10 w-px bg-gray-700" />
            <div>
              <span className="text-sm text-gray-500">Customer</span>
              <p className="text-white">{mockOrder.customer_name}</p>
            </div>
          </div>

          {/* Right: Status Badge */}
          <div className={`px-4 py-2 rounded-lg border ${getStatusBgColor(mockOrder.status)}`}>
            {mockOrder.status === 'incomplete' ? (
              <div className="flex items-center gap-3">
                <span className={`font-medium ${getStatusColor(mockOrder.status)}`}>
                  {presentRequiredCount}/{requiredFields.length} Fields
                </span>
                {getStatusMessage() && (
                  <span className="text-gray-400 text-sm">
                    {getStatusMessage()}
                  </span>
                )}
              </div>
            ) : mockOrder.status === 'ready' ? (
              <span className={`font-medium ${getStatusColor(mockOrder.status)}`}>
                Ready to Create
              </span>
            ) : (
              <div className="flex items-center gap-3">
                <span className={`font-medium ${getStatusColor(mockOrder.status)}`}>
                  Order #{mockOrder.htc_order_number}
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
            {requiredFields.map(field => (
              <FieldRow
                key={field.name}
                field={field}
                onConflictSelect={handleConflictSelect}
              />
            ))}
          </div>

          {/* Optional Fields */}
          <div className="mt-6 space-y-2">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Optional ({optionalFields.filter(getEffectiveValue).length}/{optionalFields.length})
            </h3>
            {optionalFields.map(field => (
              <FieldRow
                key={field.name}
                field={field}
                onConflictSelect={handleConflictSelect}
              />
            ))}
          </div>
        </div>

        {/* Right Column - Data Sources */}
        <div className="w-80 flex-shrink-0 overflow-auto p-6 bg-gray-800/30 flex flex-col">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Sources ({mockDataSources.length} PDFs)
          </h3>

          <div className="space-y-3 flex-1">
            {mockDataSources.map((source, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-gray-600 bg-gray-800 p-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate text-white">
                    {source.pdfFilename}
                  </p>
                  <p className="text-xs text-gray-500 truncate mt-0.5">
                    {source.emailSubject}
                  </p>
                </div>

                <div className="mt-2 flex flex-wrap gap-1">
                  {source.fieldsContributed.map(fieldName => (
                    <span
                      key={fieldName}
                      className="text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-300"
                    >
                      {fieldName.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* View All PDFs Button */}
          <button
            onClick={handleViewAllPdfs}
            className="mt-4 w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            View All PDFs
          </button>
        </div>
      </div>
    </div>
  );
}
