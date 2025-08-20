export interface EtoRun {
  id: string;

  // File information
  fileId: string;
  fileName: string;
  filePath: string;
  fileSize: number;
  sha256: string;

  // Source information
  sourceEmailId?: string;
  sourceEmailSubject?: string;
  sourceEmailFrom?: string;
  receivedAt: Date;

  // Processing status
  status: "success" | "failure" | "unrecognized";

  // Template matching
  matchedTemplateId?: string;
  matchedTemplateName?: string;
  matchConfidence?: number;

  // Extraction results (for success/failure)
  extractedFields?: {
    [fieldName: string]: {
      value: string;
      confidence: number;
      bbox?: [number, number, number, number];
      page: number;
    };
  };

  // Error information (for failure)
  errorDetails?: {
    errorType:
      | "template_not_found"
      | "extraction_failed"
      | "validation_failed"
      | "processing_error";
    errorMessage: string;
    errorCode?: string;
    failedAt: Date;
  };

  // Processing metadata
  processingStartedAt: Date;
  processingCompletedAt?: Date;
  processingDuration?: number; // milliseconds

  // Job information
  jobId: string;
  jobStatus: "pending" | "processing" | "completed" | "failed";

  // User actions
  reviewedBy?: string;
  reviewedAt?: Date;
  reviewNotes?: string;
  manuallyCorrected?: boolean;

  // System metadata
  createdAt: Date;
  updatedAt: Date;
  version: number;
}

export interface EtoRunSummary {
  id: string;
  fileName: string;
  status: "success" | "failure" | "unrecognized";
  receivedAt: Date;
  processingCompletedAt?: Date;
  matchedTemplateName?: string;
  extractedFieldCount?: number;
  errorMessage?: string;
  reviewedBy?: string;
  reviewedAt?: Date;
}

export const mockEtoRuns: EtoRun[] = [
  // Success runs
  {
    id: "1",
    fileId: "file-001",
    fileName: "BOL_ABC_2024_001.pdf",
    filePath: "/storage/files/BOL_ABC_2024_001.pdf",
    fileSize: 245760,
    sha256: "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
    sourceEmailId: "email-001",
    sourceEmailSubject: "BOL for Shipment ABC-2024-001",
    sourceEmailFrom: "shipping@abclogistics.com",
    receivedAt: new Date("2024-03-21T10:30:00Z"),
    status: "success",
    matchedTemplateId: "template-001",
    matchedTemplateName: "Standard BOL Template",
    matchConfidence: 0.95,
    extractedFields: {
      bol_number: { value: "BOL-2024-001", confidence: 0.98, page: 0 },
      shipper_name: { value: "ABC Logistics", confidence: 0.95, page: 0 },
      consignee_name: { value: "XYZ Manufacturing", confidence: 0.92, page: 0 },
      delivery_date: { value: "2024-03-25", confidence: 0.89, page: 0 },
      total_weight: { value: "1,250 lbs", confidence: 0.94, page: 0 },
    },
    processingStartedAt: new Date("2024-03-21T10:31:00Z"),
    processingCompletedAt: new Date("2024-03-21T10:31:45Z"),
    processingDuration: 45000,
    jobId: "job-001",
    jobStatus: "completed",
    createdAt: new Date("2024-03-21T10:30:00Z"),
    updatedAt: new Date("2024-03-21T10:31:45Z"),
    version: 1,
  },
  {
    id: "2",
    fileId: "file-002",
    fileName: "Receipt_XYZ_2024_002.pdf",
    filePath: "/storage/files/Receipt_XYZ_2024_002.pdf",
    fileSize: 189440,
    sha256: "b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678",
    sourceEmailId: "email-002",
    sourceEmailSubject: "Receipt for PO #12345",
    sourceEmailFrom: "receiving@xyzmanufacturing.com",
    receivedAt: new Date("2024-03-21T11:15:00Z"),
    status: "success",
    matchedTemplateId: "template-002",
    matchedTemplateName: "Custom Receipt Template",
    matchConfidence: 0.92,
    extractedFields: {
      po_number: { value: "PO-12345", confidence: 0.96, page: 0 },
      part_number: { value: "PN-789", confidence: 0.94, page: 0 },
      quantity: { value: "50", confidence: 0.91, page: 0 },
      received_date: { value: "2024-03-21", confidence: 0.88, page: 0 },
    },
    processingStartedAt: new Date("2024-03-21T11:16:00Z"),
    processingCompletedAt: new Date("2024-03-21T11:16:30Z"),
    processingDuration: 30000,
    jobId: "job-002",
    jobStatus: "completed",
    createdAt: new Date("2024-03-21T11:15:00Z"),
    updatedAt: new Date("2024-03-21T11:16:30Z"),
    version: 1,
  },
  {
    id: "3",
    fileId: "file-003",
    fileName: "BOL_ABC_2024_003.pdf",
    filePath: "/storage/files/BOL_ABC_2024_003.pdf",
    fileSize: 267520,
    sha256: "c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890",
    sourceEmailId: "email-003",
    sourceEmailSubject: "BOL for Shipment ABC-2024-003",
    sourceEmailFrom: "shipping@abclogistics.com",
    receivedAt: new Date("2024-03-21T14:20:00Z"),
    status: "success",
    matchedTemplateId: "template-001",
    matchedTemplateName: "Standard BOL Template",
    matchConfidence: 0.97,
    extractedFields: {
      bol_number: { value: "BOL-2024-003", confidence: 0.99, page: 0 },
      shipper_name: { value: "ABC Logistics", confidence: 0.96, page: 0 },
      consignee_name: { value: "DEF Industries", confidence: 0.93, page: 0 },
      delivery_date: { value: "2024-03-28", confidence: 0.9, page: 0 },
      total_weight: { value: "2,100 lbs", confidence: 0.95, page: 0 },
    },
    processingStartedAt: new Date("2024-03-21T14:21:00Z"),
    processingCompletedAt: new Date("2024-03-21T14:21:35Z"),
    processingDuration: 35000,
    jobId: "job-003",
    jobStatus: "completed",
    createdAt: new Date("2024-03-21T14:20:00Z"),
    updatedAt: new Date("2024-03-21T14:21:35Z"),
    version: 1,
  },

  // Failure runs
  {
    id: "4",
    fileId: "file-004",
    fileName: "BOL_ABC_2024_004.pdf",
    filePath: "/storage/files/BOL_ABC_2024_004.pdf",
    fileSize: 198656,
    sha256: "d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890ab",
    sourceEmailId: "email-004",
    sourceEmailSubject: "BOL for Shipment ABC-2024-004",
    sourceEmailFrom: "shipping@abclogistics.com",
    receivedAt: new Date("2024-03-21T15:45:00Z"),
    status: "failure",
    matchedTemplateId: "template-001",
    matchedTemplateName: "Standard BOL Template",
    matchConfidence: 0.85,
    errorDetails: {
      errorType: "extraction_failed",
      errorMessage:
        "Failed to extract BOL number: field not found in expected location",
      errorCode: "EXTRACT_001",
      failedAt: new Date("2024-03-21T15:46:00Z"),
    },
    processingStartedAt: new Date("2024-03-21T15:46:00Z"),
    processingCompletedAt: new Date("2024-03-21T15:46:45Z"),
    processingDuration: 45000,
    jobId: "job-004",
    jobStatus: "failed",
    reviewedBy: "admin@company.com",
    reviewedAt: new Date("2024-03-21T16:00:00Z"),
    reviewNotes:
      "BOL number field appears to be in different location than expected",
    manuallyCorrected: true,
    createdAt: new Date("2024-03-21T15:45:00Z"),
    updatedAt: new Date("2024-03-21T16:00:00Z"),
    version: 1,
  },
  {
    id: "5",
    fileId: "file-005",
    fileName: "Receipt_XYZ_2024_005.pdf",
    filePath: "/storage/files/Receipt_XYZ_2024_005.pdf",
    fileSize: 156672,
    sha256: "e5f6789012345678901234567890abcdef1234567890abcdef1234567890abcd",
    sourceEmailId: "email-005",
    sourceEmailSubject: "Receipt for PO #12346",
    sourceEmailFrom: "receiving@xyzmanufacturing.com",
    receivedAt: new Date("2024-03-21T16:30:00Z"),
    status: "failure",
    matchedTemplateId: "template-002",
    matchedTemplateName: "Custom Receipt Template",
    matchConfidence: 0.78,
    errorDetails: {
      errorType: "validation_failed",
      errorMessage:
        'Extracted quantity value "invalid" does not match expected numeric format',
      errorCode: "VALID_001",
      failedAt: new Date("2024-03-21T16:31:00Z"),
    },
    processingStartedAt: new Date("2024-03-21T16:31:00Z"),
    processingCompletedAt: new Date("2024-03-21T16:31:25Z"),
    processingDuration: 25000,
    jobId: "job-005",
    jobStatus: "failed",
    createdAt: new Date("2024-03-21T16:30:00Z"),
    updatedAt: new Date("2024-03-21T16:31:25Z"),
    version: 1,
  },

  // Unrecognized runs
  {
    id: "6",
    fileId: "file-006",
    fileName: "Invoice_NewCorp_2024_001.pdf",
    filePath: "/storage/files/Invoice_NewCorp_2024_001.pdf",
    fileSize: 312832,
    sha256: "f6789012345678901234567890abcdef1234567890abcdef1234567890abcdef",
    sourceEmailId: "email-006",
    sourceEmailSubject: "Invoice for Services Rendered",
    sourceEmailFrom: "billing@newcorp.com",
    receivedAt: new Date("2024-03-21T17:00:00Z"),
    status: "unrecognized",
    processingStartedAt: new Date("2024-03-21T17:01:00Z"),
    processingCompletedAt: new Date("2024-03-21T17:01:15Z"),
    processingDuration: 15000,
    jobId: "job-006",
    jobStatus: "completed",
    createdAt: new Date("2024-03-21T17:00:00Z"),
    updatedAt: new Date("2024-03-21T17:01:15Z"),
    version: 1,
  },
  {
    id: "7",
    fileId: "file-007",
    fileName: "Contract_LegacyCorp_2024_001.pdf",
    filePath: "/storage/files/Contract_LegacyCorp_2024_001.pdf",
    fileSize: 892416,
    sha256: "6789012345678901234567890abcdef1234567890abcdef1234567890abcdef12",
    sourceEmailId: "email-007",
    sourceEmailSubject: "Contract Agreement",
    sourceEmailFrom: "legal@legacycorp.com",
    receivedAt: new Date("2024-03-21T18:15:00Z"),
    status: "unrecognized",
    processingStartedAt: new Date("2024-03-21T18:16:00Z"),
    processingCompletedAt: new Date("2024-03-21T18:16:10Z"),
    processingDuration: 10000,
    jobId: "job-007",
    jobStatus: "completed",
    createdAt: new Date("2024-03-21T18:15:00Z"),
    updatedAt: new Date("2024-03-21T18:16:10Z"),
    version: 1,
  },
  {
    id: "8",
    fileId: "file-008",
    fileName: "Quote_NewVendor_2024_001.pdf",
    filePath: "/storage/files/Quote_NewVendor_2024_001.pdf",
    fileSize: 178688,
    sha256:
      "7890123456789012345678901234567890abcdef1234567890abcdef1234567890",
    sourceEmailId: "email-008",
    sourceEmailSubject: "Quote for Equipment",
    sourceEmailFrom: "sales@newvendor.com",
    receivedAt: new Date("2024-03-21T19:30:00Z"),
    status: "unrecognized",
    processingStartedAt: new Date("2024-03-21T19:31:00Z"),
    processingCompletedAt: new Date("2024-03-21T19:31:08Z"),
    processingDuration: 8000,
    jobId: "job-008",
    jobStatus: "completed",
    createdAt: new Date("2024-03-21T19:30:00Z"),
    updatedAt: new Date("2024-03-21T19:31:08Z"),
    version: 1,
  },
];

// Helper function to get summary data
export function getEtoRunSummary(run: EtoRun): EtoRunSummary {
  return {
    id: run.id,
    fileName: run.fileName,
    status: run.status,
    receivedAt: run.receivedAt,
    processingCompletedAt: run.processingCompletedAt,
    matchedTemplateName: run.matchedTemplateName,
    extractedFieldCount: run.extractedFields
      ? Object.keys(run.extractedFields).length
      : undefined,
    errorMessage: run.errorDetails?.errorMessage,
    reviewedBy: run.reviewedBy,
    reviewedAt: run.reviewedAt,
  };
}
