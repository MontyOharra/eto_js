// Mock data for ETO run detail view
import { EtoRunDetail } from '../types';

export const mockEtoRunDetail: EtoRunDetail = {
  id: 2,
  pdfFilename: 'receipts_jan_2024.pdf',
  source: 'Manual Upload',
  sourceDate: '2024-01-15 10:40:18',
  masterStatus: 'failure',
  totalPages: 15,
  createdAt: '2024-01-15 10:45:32',
  lastUpdated: '2024-01-15 11:02:14',
  processingStep: 'sub_runs',

  // PDF file info
  pdfFile: {
    id: 123,
    storagePath: '/storage/uploads/receipts_jan_2024.pdf',
    fileSize: '3.8 MB',
  },

  // Email details (if from email)
  emailDetails: null,

  // Matched sub-runs (with template matches)
  matchedSubRuns: [
    {
      id: 1,
      pages: [1, 2, 3],
      status: 'success',
      template: {
        id: 5,
        name: 'Vendor Receipt Template',
        description: 'Standard vendor receipt format',
      },
      extractedData: {
        vendor: 'ABC Supply Co.',
        total: '$1,245.67',
        date: '2024-01-10',
        invoiceNumber: 'INV-2024-001',
        poNumber: 'PO-9876',
      },
      processedAt: '2024-01-15 10:52:08',
      errorMessage: null,
    },
    {
      id: 2,
      pages: [4, 5],
      status: 'success',
      template: {
        id: 5,
        name: 'Vendor Receipt Template',
        description: 'Standard vendor receipt format',
      },
      extractedData: {
        vendor: 'XYZ Hardware',
        total: '$842.33',
        date: '2024-01-12',
        invoiceNumber: 'INV-2024-045',
        poNumber: 'PO-9877',
      },
      processedAt: '2024-01-15 10:58:22',
      errorMessage: null,
    },
    {
      id: 3,
      pages: [8, 9],
      status: 'failure',
      template: {
        id: 7,
        name: 'Shipping Invoice Template',
        description: 'UPS/FedEx shipping invoice format',
      },
      extractedData: null,
      processedAt: '2024-01-15 11:01:45',
      errorMessage: 'Failed to extract tracking number: OCR confidence too low (0.42)',
    },
    {
      id: 4,
      pages: [12],
      status: 'failure',
      template: {
        id: 5,
        name: 'Vendor Receipt Template',
        description: 'Standard vendor receipt format',
      },
      extractedData: null,
      processedAt: '2024-01-15 11:02:10',
      errorMessage: 'Missing required field: total amount not found in expected region',
    },
  ],

  // Needs template sub-runs (no template match found)
  needsTemplateSubRuns: [
    {
      id: 5,
      pages: [6, 7],
      status: 'needs_template',
      createdAt: '2024-01-15 10:47:22',
    },
    {
      id: 6,
      pages: [13],
      status: 'needs_template',
      createdAt: '2024-01-15 10:47:22',
    },
  ],

  // Skipped sub-runs (user explicitly skipped)
  skippedSubRuns: [
    {
      id: 7,
      pages: [10, 11, 14, 15],
      status: 'skipped',
      skippedAt: '2024-01-15 11:05:18',
      skippedReason: 'Consolidated from failed extraction attempts',
    },
  ],
};

// Helper to get mock detail by ID (returns same mock for now, can be extended)
export function getMockEtoRunDetailById(id: number): EtoRunDetail | null {
  // For now, return the same mock data regardless of ID
  // In the future, this could return different mock data based on ID
  return {
    ...mockEtoRunDetail,
    id,
  };
}
