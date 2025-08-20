export interface EmailConfig {
  host: string;
  port: number;
  secure: boolean;
  username: string;
  password: string;
  folder: string;
}

export interface EmailMessage {
  id: string;
  subject: string;
  from: string;
  to: string[];
  date: Date;
  attachments: EmailAttachment[];
}

export interface EmailAttachment {
  filename: string;
  contentType: string;
  size: number;
  content: Buffer;
}

export interface ProcessedAttachment {
  filename: string;
  contentType: string;
  size: number;
  sha256: string;
  filePath: string;
  messageId: string;
}

export interface EmailIngestResult {
  processedCount: number;
  savedFiles: ProcessedAttachment[];
  errors: string[];
}
