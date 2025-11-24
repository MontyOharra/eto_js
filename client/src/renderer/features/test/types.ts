// Domain types for test feature

// =============================================================================
// ETO Run List Types
// =============================================================================

export type EtoRunMasterStatus =
  | 'success'
  | 'processing'
  | 'failure'
  | 'not_started'
  | 'skipped';

export interface SubRunStatuses {
  success: number;
  failure: number;
  needs_template: number;
}

export interface EtoRunListItem {
  id: number;
  pdfFilename: string;
  source: string;
  sourceSubject: string | null;
  sourceDate: string;
  masterStatus: EtoRunMasterStatus;
  totalPages: number;
  createdAt: string;
  lastUpdated: string;
  templatesMatched: number;
  pagesMatched: number;
  pagesUnmatched: number;
  isRead: boolean;
  subRunStatuses: SubRunStatuses;
}

// =============================================================================
// ETO Run Detail Types
// =============================================================================

export interface PdfFileInfo {
  id: number;
  storagePath: string;
  fileSize: string;
}

export interface EmailDetails {
  from: string;
  subject: string;
  receivedAt: string;
}

export interface TemplateInfo {
  id: number;
  name: string;
  description: string;
}

export interface MatchedSubRun {
  id: number;
  pages: number[];
  status: 'success' | 'failure';
  template: TemplateInfo;
  extractedData: Record<string, string> | null;
  processedAt: string;
  errorMessage: string | null;
}

export interface NeedsTemplateSubRun {
  id: number;
  pages: number[];
  status: 'needs_template';
  createdAt: string;
}

export interface SkippedSubRun {
  id: number;
  pages: number[];
  status: 'skipped';
  skippedAt: string;
  skippedReason: string;
}

export interface EtoRunDetail {
  id: number;
  pdfFilename: string;
  source: string;
  sourceDate: string;
  masterStatus: EtoRunMasterStatus;
  totalPages: number;
  createdAt: string;
  lastUpdated: string;
  processingStep: string;
  pdfFile: PdfFileInfo;
  emailDetails: EmailDetails | null;
  matchedSubRuns: MatchedSubRun[];
  needsTemplateSubRuns: NeedsTemplateSubRun[];
  skippedSubRuns: SkippedSubRun[];
}

// =============================================================================
// Multi-Template Test Types
// =============================================================================

export interface TemplateMatch {
  template_name: string;
  version_number: number;
  matched_pages: number[];
}

export interface MultiTemplateTestResult {
  pdf_filename: string;
  pdf_id: number;
  total_pages: number;
  matches: TemplateMatch[];
  unmatched_pages: number[];
}
