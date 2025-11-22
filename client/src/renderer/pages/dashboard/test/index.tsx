import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { Table } from '../../../features/test';
import { useState } from 'react';

export const Route = createFileRoute('/dashboard/test/')({
  component: TestPage,
});

// Mock data
const mockData = [
  {
    id: 1,
    pdfFilename: 'invoice_batch_2024.pdf',
    source: 'accounting@company.com',
    sourceSubject: 'January Invoice Batch',
    sourceDate: '2024-01-15 09:15',
    masterStatus: 'success',
    totalPages: 12,
    createdAt: '2024-01-15 09:20',
    lastUpdated: '2024-01-15 09:25',
    templatesMatched: 3,
    pagesMatched: 12,
    pagesUnmatched: 0,
    isRead: true,
    subRunStatuses: { success: 3, failure: 0, needs_template: 0 }, // All succeeded
  },
  {
    id: 2,
    pdfFilename: 'receipts_jan_2024.pdf',
    source: 'Manual Upload',
    sourceSubject: null,
    sourceDate: '2024-01-15 10:30',
    masterStatus: 'success',
    totalPages: 8,
    createdAt: '2024-01-15 10:35',
    lastUpdated: '2024-01-15 11:20',
    templatesMatched: 1,
    pagesMatched: 5,
    pagesUnmatched: 3,
    isRead: false,
    subRunStatuses: { success: 1, failure: 0, needs_template: 1 }, // Success + needs template
  },
  {
    id: 3,
    pdfFilename: 'mixed_documents.pdf',
    source: 'receipts@vendor.com',
    sourceSubject: 'Re: Outstanding receipts for review',
    sourceDate: '2024-01-15 11:05',
    masterStatus: 'failure',
    totalPages: 6,
    createdAt: '2024-01-15 11:08',
    lastUpdated: '2024-01-15 11:12',
    templatesMatched: 0,
    pagesMatched: 0,
    pagesUnmatched: 0,
    isRead: false,
    subRunStatuses: { success: 0, failure: 0, needs_template: 0 }, // Parent-level failure, no sub-runs
  },
  {
    id: 4,
    pdfFilename: 'weekly_statements.pdf',
    source: 'billing@service.com',
    sourceSubject: 'Weekly Account Statements - Week Ending January 12, 2024',
    sourceDate: '2024-01-15 11:45',
    masterStatus: 'not_started',
    totalPages: 20,
    createdAt: '2024-01-15 11:48',
    lastUpdated: '2024-01-15 11:50',
    templatesMatched: 0,
    pagesMatched: 0,
    pagesUnmatched: 0,
    isRead: true,
    subRunStatuses: { success: 0, failure: 0, needs_template: 0 }, // Not started yet
  },
  {
    id: 5,
    pdfFilename: 'purchase_orders.pdf',
    source: 'Manual Upload',
    sourceSubject: null,
    sourceDate: '2024-01-14 16:15',
    masterStatus: 'success',
    totalPages: 15,
    createdAt: '2024-01-14 16:20',
    lastUpdated: '2024-01-14 16:42',
    templatesMatched: 5,
    pagesMatched: 15,
    pagesUnmatched: 0,
    isRead: true,
    subRunStatuses: { success: 5, failure: 0, needs_template: 0 }, // All succeeded
  },
  {
    id: 6,
    pdfFilename: 'vendor_invoices.pdf',
    source: 'invoices@vendor.com',
    sourceSubject: 'Invoices',
    sourceDate: '2024-01-15 12:00',
    masterStatus: 'success',
    totalPages: 10,
    createdAt: '2024-01-15 12:05',
    lastUpdated: '2024-01-15 12:18',
    templatesMatched: 2,
    pagesMatched: 7,
    pagesUnmatched: 3,
    isRead: false,
    subRunStatuses: { success: 2, failure: 0, needs_template: 1 }, // Success + needs template
  },
  {
    id: 7,
    pdfFilename: 'shipping_manifests_q1.pdf',
    source: 'shipping@logistics.com',
    sourceSubject: 'FW: Q1 Shipping Manifests - Please review and confirm receipt of all shipments for compliance audit',
    sourceDate: '2024-01-15 13:22',
    masterStatus: 'processing',
    totalPages: 25,
    createdAt: '2024-01-15 13:25',
    lastUpdated: '2024-01-15 13:28',
    templatesMatched: 0,
    pagesMatched: 0,
    pagesUnmatched: 0,
    isRead: false,
    subRunStatuses: { success: 0, failure: 0, needs_template: 0 }, // Still processing
  },
  {
    id: 8,
    pdfFilename: 'tax_forms_2024.pdf',
    source: 'payroll@company.com',
    sourceSubject: '2024 Tax Forms',
    sourceDate: '2024-01-15 08:05',
    masterStatus: 'success',
    totalPages: 4,
    createdAt: '2024-01-15 08:10',
    lastUpdated: '2024-01-15 08:12',
    templatesMatched: 1,
    pagesMatched: 4,
    pagesUnmatched: 0,
    isRead: true,
    subRunStatuses: { success: 1, failure: 0, needs_template: 0 }, // All succeeded
  },
  {
    id: 9,
    pdfFilename: 'contract_amendments.pdf',
    source: 'legal@vendor.com',
    sourceSubject: 'Contract Amendment Documents - Action Required',
    sourceDate: '2024-01-15 14:40',
    masterStatus: 'success',
    totalPages: 18,
    createdAt: '2024-01-15 14:42',
    lastUpdated: '2024-01-15 14:55',
    templatesMatched: 0,
    pagesMatched: 0,
    pagesUnmatched: 18,
    isRead: false,
    subRunStatuses: { success: 0, failure: 0, needs_template: 1 }, // Only needs template
  },
  {
    id: 10,
    pdfFilename: 'monthly_expense_report.pdf',
    source: 'Manual Upload',
    sourceSubject: null,
    sourceDate: '2024-01-15 15:10',
    masterStatus: 'success',
    totalPages: 3,
    createdAt: '2024-01-15 15:12',
    lastUpdated: '2024-01-15 15:14',
    templatesMatched: 1,
    pagesMatched: 3,
    pagesUnmatched: 0,
    isRead: false,
    subRunStatuses: { success: 1, failure: 0, needs_template: 0 }, // All succeeded
  },
  {
    id: 11,
    pdfFilename: 'supplier_quotes_batch.pdf',
    source: 'quotes@suppliers.com',
    sourceSubject: 'Quotes for Office Supplies',
    sourceDate: '2024-01-15 07:30',
    masterStatus: 'success',
    totalPages: 22,
    createdAt: '2024-01-15 07:35',
    lastUpdated: '2024-01-15 07:48',
    templatesMatched: 4,
    pagesMatched: 20,
    pagesUnmatched: 2,
    isRead: true,
    subRunStatuses: { success: 4, failure: 0, needs_template: 1 }, // Success + needs template
  },
  {
    id: 12,
    pdfFilename: 'delivery_confirmations.pdf',
    source: 'delivery@courier.com',
    sourceSubject: 'Delivery Confirmations - Batch #4521',
    sourceDate: '2024-01-15 16:05',
    masterStatus: 'success',
    totalPages: 7,
    createdAt: '2024-01-15 16:08',
    lastUpdated: '2024-01-15 16:15',
    templatesMatched: 2,
    pagesMatched: 5,
    pagesUnmatched: 2,
    isRead: false,
    subRunStatuses: { success: 2, failure: 0, needs_template: 1 }, // Success + needs template
  },
  {
    id: 13,
    pdfFilename: 'insurance_claims.pdf',
    source: 'claims@insurance.com',
    sourceSubject: 'Re: Claim #INS-2024-0142',
    sourceDate: '2024-01-14 14:22',
    masterStatus: 'success',
    totalPages: 9,
    createdAt: '2024-01-14 14:25',
    lastUpdated: '2024-01-14 14:32',
    templatesMatched: 1,
    pagesMatched: 6,
    pagesUnmatched: 3,
    isRead: true,
    subRunStatuses: { success: 1, failure: 1, needs_template: 1 }, // All three statuses!
  },
  {
    id: 14,
    pdfFilename: 'audit_documents_2024.pdf',
    source: 'audit@external.com',
    sourceSubject: null,
    sourceDate: '2024-01-15 09:55',
    masterStatus: 'skipped',
    totalPages: 45,
    createdAt: '2024-01-15 10:00',
    lastUpdated: '2024-01-15 10:02',
    templatesMatched: 0,
    pagesMatched: 0,
    pagesUnmatched: 0,
    isRead: false,
    subRunStatuses: { success: 0, failure: 0, needs_template: 0 }, // Skipped, no sub-runs
  },
  {
    id: 15,
    pdfFilename: 'customer_orders_daily.pdf',
    source: 'orders@ecommerce.com',
    sourceSubject: 'Daily Order Summary - January 15',
    sourceDate: '2024-01-15 17:00',
    masterStatus: 'success',
    totalPages: 35,
    createdAt: '2024-01-15 17:02',
    lastUpdated: '2024-01-15 17:20',
    templatesMatched: 7,
    pagesMatched: 35,
    pagesUnmatched: 0,
    isRead: false,
    subRunStatuses: { success: 7, failure: 0, needs_template: 0 }, // All succeeded
  },
  {
    id: 16,
    pdfFilename: 'payment_receipts.pdf',
    source: 'payments@bank.com',
    sourceSubject: 'Payment Receipt',
    sourceDate: '2024-01-15 11:30',
    masterStatus: 'success',
    totalPages: 12,
    createdAt: '2024-01-15 11:33',
    lastUpdated: '2024-01-15 11:40',
    templatesMatched: 3,
    pagesMatched: 10,
    pagesUnmatched: 2,
    isRead: true,
    subRunStatuses: { success: 3, failure: 0, needs_template: 1 }, // Success + needs template
  },
  {
    id: 17,
    pdfFilename: 'regulatory_filing.pdf',
    source: 'compliance@regulator.gov',
    sourceSubject: 'Annual Regulatory Compliance Filing Documentation and Supporting Materials for Fiscal Year 2024 Review',
    sourceDate: '2024-01-14 16:45',
    masterStatus: 'failure',
    totalPages: 8,
    createdAt: '2024-01-14 16:50',
    lastUpdated: '2024-01-14 16:51',
    templatesMatched: 0,
    pagesMatched: 0,
    pagesUnmatched: 0,
    isRead: false,
    subRunStatuses: { success: 0, failure: 0, needs_template: 0 }, // Parent-level failure, no sub-runs
  },
  {
    id: 18,
    pdfFilename: 'maintenance_logs.pdf',
    source: 'Manual Upload',
    sourceSubject: null,
    sourceDate: '2024-01-15 08:20',
    masterStatus: 'success',
    totalPages: 6,
    createdAt: '2024-01-15 08:22',
    lastUpdated: '2024-01-15 08:25',
    templatesMatched: 1,
    pagesMatched: 6,
    pagesUnmatched: 0,
    isRead: true,
    subRunStatuses: { success: 1, failure: 0, needs_template: 0 }, // All succeeded
  },
  {
    id: 19,
    pdfFilename: 'warranty_claims_batch.pdf',
    source: 'warranty@manufacturer.com',
    sourceSubject: 'Warranty Claims - Batch Processing Required',
    sourceDate: '2024-01-15 13:10',
    masterStatus: 'success',
    totalPages: 14,
    createdAt: '2024-01-15 13:12',
    lastUpdated: '2024-01-15 13:22',
    templatesMatched: 2,
    pagesMatched: 12,
    pagesUnmatched: 2,
    isRead: false,
    subRunStatuses: { success: 2, failure: 1, needs_template: 0 }, // Success + failure
  },
  {
    id: 20,
    pdfFilename: 'training_certificates.pdf',
    source: 'hr@company.com',
    sourceSubject: 'Q1 Training Certificates',
    sourceDate: '2024-01-15 10:15',
    masterStatus: 'success',
    totalPages: 5,
    createdAt: '2024-01-15 10:18',
    lastUpdated: '2024-01-15 10:20',
    templatesMatched: 1,
    pagesMatched: 5,
    pagesUnmatched: 0,
    isRead: true,
    subRunStatuses: { success: 1, failure: 0, needs_template: 0 }, // All succeeded
  },
];

interface EtoRunRowProps {
  data: {
    id: number;
    pdfFilename: string;
    source: string;
    sourceSubject: string | null;
    sourceDate: string;
    masterStatus: string;
    totalPages: number;
    createdAt: string;
    lastUpdated: string;
    templatesMatched: number;
    pagesMatched: number;
    pagesUnmatched: number;
    isRead: boolean;
    subRunStatuses: {
      success: number;
      failure: number;
      needs_template: number;
    };
  };
  onClick: () => void;
}

function EtoRunRow({ data, onClick }: EtoRunRowProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-green-400';
      case 'processing':
        return 'text-blue-400';
      case 'failure':
        return 'text-red-400';
      case 'not_started':
        return 'text-gray-400';
      default:
        return 'text-gray-400';
    }
  };

  const formatPageBreakdown = () => {
    if (data.pagesMatched === 0 && data.pagesUnmatched === 0) return '-';
    const parts = [];
    if (data.pagesMatched > 0) parts.push(`${data.pagesMatched} matched`);
    if (data.pagesUnmatched > 0) parts.push(`${data.pagesUnmatched} unmatched`);
    return parts.join(', ');
  };

  // Determine which indicators to show based on sub-run statuses
  const hasSubRuns = data.subRunStatuses.success > 0 || data.subRunStatuses.failure > 0 || data.subRunStatuses.needs_template > 0;
  const showIndicators = hasSubRuns;

  const indicators = [];
  if (showIndicators) {
    if (data.subRunStatuses.success > 0) {
      indicators.push({ color: 'green', ping: 'bg-green-400', solid: 'bg-green-500' });
    }
    if (data.subRunStatuses.needs_template > 0) {
      indicators.push({ color: 'yellow', ping: 'bg-yellow-400', solid: 'bg-yellow-500' });
    }
    if (data.subRunStatuses.failure > 0) {
      indicators.push({ color: 'red', ping: 'bg-red-400', solid: 'bg-red-500' });
    }
  }

  // Determine if row should be dimmed (read items)
  const isRead = data.isRead;
  const textOpacity = isRead ? 'opacity-60' : 'opacity-100';

  // Determine if this is a failure row (parent-level failure)
  const isFailure = data.masterStatus === 'failure';
  const filenameColor = isFailure
    ? 'text-red-300'
    : (isRead ? 'text-gray-400' : 'text-gray-200');

  // Row background and border for failures
  const rowBg = isFailure ? 'bg-red-900/10 border-l-2 border-red-500/50' : '';

  // Determine which action buttons to show
  const isSkipped = data.masterStatus === 'skipped';
  const hasIssues = data.subRunStatuses.failure > 0 || data.subRunStatuses.needs_template > 0;
  const isFullySuccessful = data.masterStatus === 'success' && !hasIssues;

  // Skip button: Show if run has failures/needs_template (but not if already skipped)
  const showSkipButton = !isSkipped && (data.masterStatus === 'failure' || hasIssues);

  // Delete button: Only show for skipped runs (replaces skip button)
  const showDeleteButton = isSkipped;

  // Reprocess button: Show for anything except fully successful or skipped
  const showReprocessButton = !isFullySuccessful && !isSkipped;

  // View PDF and Mark Read/Unread: Always show
  const showViewPdfButton = true;
  const showReadToggle = true;

  return (
    <button
      onClick={onClick}
      className={`w-full py-2.5 hover:bg-gray-700/30 transition-colors cursor-pointer text-left group ${rowBg}`}
    >
      <div className="px-6">
        <div className="grid gap-4" style={{ gridTemplateColumns: '2fr 2fr 1fr 100px 1fr auto 400px' }}>
        {/* PDF Filename with fixed-width indicator area */}
        <div className={`flex items-center gap-2 min-w-0 ${textOpacity}`}>
          {/* Fixed width area for indicators - always takes same space */}
          <div className="w-8 flex items-center gap-1 flex-shrink-0 self-center">
            {showIndicators && indicators.length > 0 && (
              <>
                {indicators.map((indicator, index) => (
                  <span key={index} className="relative flex h-2 w-2">
                    {/* Only show pulsing animation for unread items */}
                    {!isRead && (
                      <span className={`animate-ping absolute inset-0 rounded-full ${indicator.ping} opacity-75`}></span>
                    )}
                    <span className={`relative inline-flex rounded-full h-2 w-2 ${indicator.solid} ${isRead ? 'opacity-40' : ''}`}></span>
                  </span>
                ))}
              </>
            )}
          </div>
          <span className={`${filenameColor} text-sm ${!isRead ? 'font-medium' : ''} break-words min-w-0`}>{data.pdfFilename}</span>
        </div>

        {/* Source column with subject line below */}
        <div className={`flex flex-col gap-0.5 min-w-0 self-center ${textOpacity}`}>
          <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} break-words`}>
            {data.source}
          </span>
          {data.sourceSubject && (
            <span className={`text-xs ${isFailure ? 'text-red-200/50' : 'text-gray-500'} break-words`}>
              {data.sourceSubject}
            </span>
          )}
        </div>
        <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} break-words self-center ${textOpacity}`}>{data.sourceDate}</span>
        <span className={`text-sm font-semibold ${getStatusColor(data.masterStatus)} break-words self-center ${textOpacity}`}>
          {data.masterStatus.replace('_', ' ')}
        </span>
        <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} break-words self-center ${textOpacity}`}>{formatPageBreakdown()}</span>
        <span className={`text-sm ${isFailure ? 'text-red-200/70' : 'text-gray-300'} break-words self-center ${textOpacity}`}>{data.lastUpdated}</span>

        {/* Action Buttons - Always visible, disabled when not applicable */}
        <div className="flex items-center gap-1.5 justify-end self-center">
          {/* Skip/Delete button - mutually exclusive */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (showDeleteButton) {
                // Handle delete action
              } else if (showSkipButton) {
                // Handle skip action
              }
            }}
            disabled={!showSkipButton && !showDeleteButton}
            className={`w-16 px-2 py-1 text-xs font-medium rounded transition-colors ${
              showDeleteButton
                ? 'bg-red-900/30 hover:bg-red-700/50 text-red-400 hover:text-red-300'
                : showSkipButton
                ? 'bg-yellow-900/30 hover:bg-yellow-700/50 text-yellow-400 hover:text-yellow-300'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
            title={
              showDeleteButton
                ? 'Delete this run'
                : showSkipButton
                ? 'Skip this run'
                : 'No action needed'
            }
          >
            {showDeleteButton ? 'Delete' : 'Skip'}
          </button>

          {/* Reprocess button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (showReprocessButton) {
                // Handle reprocess action
              }
            }}
            disabled={!showReprocessButton}
            className={`w-20 px-2 py-1 text-xs font-medium rounded transition-colors ${
              showReprocessButton
                ? 'bg-green-900/30 hover:bg-green-700/50 text-green-400 hover:text-green-300'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
            title={showReprocessButton ? 'Reprocess failed items' : 'No reprocessing needed'}
          >
            Reprocess
          </button>

          {/* View PDF button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              // Handle view PDF action
            }}
            className="w-20 px-2 py-1 text-xs font-medium bg-blue-900/30 hover:bg-blue-700/50 text-blue-400 hover:text-blue-300 rounded transition-colors whitespace-nowrap"
            title="View PDF"
          >
            View PDF
          </button>

          {/* Mark Read/Unread icon button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              // Handle mark read/unread toggle
            }}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-white"
            title={isRead ? 'Mark as unread' : 'Mark as read'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isRead ? (
                // Eye icon for read items
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              ) : (
                // Eye-slash icon for unread items
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              )}
            </svg>
          </button>
        </div>
        </div>
      </div>
    </button>
  );
}

function TestPage() {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRowClick = (runId: number) => {
    navigate({ to: '/dashboard/test/$runId', params: { runId: runId.toString() } });
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setTestResult(null);

    const formData = new FormData();
    formData.append('pdf_file', file);

    try {
      const response = await fetch('http://localhost:8000/api/pdf-templates/test-multi-match', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      setTestResult(result);
      console.log('Multi-template matching result:', result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      console.error('Upload error:', err);
    } finally {
      setIsUploading(false);
    }
  };

  const triggerFileInput = () => {
    document.getElementById('pdf-upload-input')?.click();
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Test Multi-Template Matching Section */}
      <div className="px-6 pt-6 pb-4 border-b border-gray-700 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Test Multi-Template Matching</h2>
            <p className="text-gray-400 text-sm">Upload a PDF to test the new algorithm</p>
          </div>
          <input
            id="pdf-upload-input"
            type="file"
            accept=".pdf"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={triggerFileInput}
            disabled={isUploading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors flex items-center gap-2"
          >
            {isUploading ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Uploading...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span>Upload PDF</span>
              </>
            )}
          </button>
        </div>

        {/* Result Display */}
        {testResult && (
          <div className="mt-4 bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="text-white font-semibold mb-2">Result:</h3>
            <div className="space-y-2 text-sm">
              <div className="flex gap-2">
                <span className="text-gray-400">PDF:</span>
                <span className="text-white">{testResult.pdf_filename} (ID: {testResult.pdf_id})</span>
              </div>
              <div className="flex gap-2">
                <span className="text-gray-400">Total Pages:</span>
                <span className="text-white">{testResult.total_pages}</span>
              </div>
              <div className="flex gap-2">
                <span className="text-gray-400">Matches:</span>
                <span className="text-green-400">{testResult.matches.length}</span>
              </div>
              <div className="flex gap-2">
                <span className="text-gray-400">Unmatched Pages:</span>
                <span className="text-yellow-400">{testResult.unmatched_pages.length}</span>
              </div>
            </div>

            {testResult.matches.length > 0 && (
              <div className="mt-4">
                <h4 className="text-white font-semibold mb-2">Template Matches:</h4>
                <div className="space-y-2">
                  {testResult.matches.map((match: any, idx: number) => (
                    <div key={idx} className="bg-gray-750 rounded p-3 border border-gray-600">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-white font-medium">{match.template_name}</span>
                        <span className="text-xs text-gray-400">v{match.version_number}</span>
                      </div>
                      <div className="text-sm text-gray-400">
                        Pages: {match.matched_pages.join(', ')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {testResult.unmatched_pages.length > 0 && (
              <div className="mt-4">
                <h4 className="text-white font-semibold mb-2">Unmatched Pages:</h4>
                <div className="text-sm text-yellow-400">
                  {testResult.unmatched_pages.join(', ')}
                </div>
              </div>
            )}

            {/* Raw JSON Output */}
            <details className="mt-4">
              <summary className="text-gray-400 cursor-pointer hover:text-white">View Raw JSON</summary>
              <pre className="mt-2 bg-gray-900 rounded p-3 text-xs text-green-400 overflow-auto max-h-60">
                {JSON.stringify(testResult, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mt-4 bg-red-900/20 border border-red-500/50 rounded-lg p-4">
            <h3 className="text-red-400 font-semibold mb-1">Error:</h3>
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        )}
      </div>

      {/* Header Section */}
      <div className="px-6 pt-6 pb-4 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-white">Test Page</h1>
          <p className="text-gray-400 mt-2">
            New ETO dashboard prototyping area
          </p>
        </div>

        {/* Search and Filter Section */}
        <div className="flex items-center gap-3">
          {/* Combined Search Input with Scope Selector */}
          <div className="flex items-center bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
            {/* Search Scope Dropdown */}
            <select
              className="px-3 py-2 bg-gray-750 text-white text-sm border-r border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              defaultValue="filename"
            >
              <option value="filename">PDF Name</option>
              <option value="email">Email</option>
              <option value="all">All Fields</option>
            </select>

            {/* Search Input */}
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Search..."
                className="w-64 px-4 py-2 pl-10 bg-gray-800 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <svg
                className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          {/* Status Filter Dropdown */}
          <select
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            defaultValue="all"
          >
            <option value="all">All Status</option>
            <option value="success">Success</option>
            <option value="processing">Processing</option>
            <option value="failure">Failure</option>
            <option value="needs_template">Needs Template</option>
            <option value="not_started">Not Started</option>
            <option value="skipped">Skipped</option>
          </select>

          {/* Read/Unread Filter */}
          <select
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            defaultValue="all"
          >
            <option value="all">All</option>
            <option value="unread">Unread</option>
            <option value="read">Read</option>
          </select>

          {/* Date Range Filter */}
          <button className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white hover:bg-gray-700 transition-colors flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span>Date Range</span>
          </button>

          {/* Clear Filters Button */}
          <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">
            Clear
          </button>
        </div>
      </div>

      {/* Results Summary & Controls */}
      <div className="px-6 pb-4 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4">
            <span className="text-gray-400 text-sm">
              <span className="text-white font-semibold">1-{mockData.length}</span> of <span className="text-white font-semibold">{mockData.length}</span>
            </span>

            {/* Pagination Controls (Gmail style) */}
            <div className="flex items-center gap-1">
              <button
                className="p-1.5 hover:bg-gray-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled
              >
                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                className="p-1.5 hover:bg-gray-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled
              >
                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>

          {/* Active Filters Pills */}
          <div className="flex items-center gap-2">
            {/* Example active filter pill */}
            {/* <div className="flex items-center gap-1 px-3 py-1 bg-blue-500/20 border border-blue-500/50 rounded-full text-blue-400 text-sm">
              <span>Status: Success</span>
              <button className="hover:text-blue-300">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div> */}
          </div>
        </div>

        {/* Sort Dropdown */}
        <select
          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          defaultValue="updated_desc"
        >
          <option value="updated_desc">Last Updated (Newest)</option>
          <option value="updated_asc">Last Updated (Oldest)</option>
          <option value="created_desc">Created (Newest)</option>
          <option value="created_asc">Created (Oldest)</option>
          <option value="filename_asc">Filename (A-Z)</option>
          <option value="filename_desc">Filename (Z-A)</option>
          <option value="status_asc">Status</option>
        </select>
      </div>

      {/* Scrollable Table Container */}
      <div className="flex-1 min-h-0 px-6 pb-6">
        <Table>
          <Table.Header>
            <div className="px-6">
              <div className="grid gap-4" style={{ gridTemplateColumns: '2fr 2fr 1fr 100px 1fr auto 400px' }}>
                {/* PDF Filename header - needs to account for 32px indicator space + 8px gap */}
                <div className="flex items-center gap-2">
                  <div className="w-8 flex-shrink-0"></div>
                  <span className="text-gray-400 font-semibold text-sm uppercase break-words">PDF Filename</span>
                </div>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Source</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Received</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Status</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Pages</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words">Last Updated</span>
                <span className="text-gray-400 font-semibold text-sm uppercase break-words text-right">Actions</span>
              </div>
            </div>
          </Table.Header>

          <Table.Body>
            {mockData.map((item, index) => (
              <div key={index}>
                <EtoRunRow data={item} onClick={() => handleRowClick(item.id)} />
                {index < mockData.length - 1 && (
                  <div className="mx-6 border-b border-gray-700" />
                )}
              </div>
            ))}
          </Table.Body>
        </Table>
      </div>
    </div>
  );
}
