/**
 * Mock Email API
 * Provides email data for PDFs that came from emails
 */

export interface EmailData {
  id: number;
  sender_email: string;
  received_date: string;
  subject: string | null;
  folder_name: string;
}

// Mock email database - maps email_id to email data
const mockEmails: Record<number, EmailData> = {
  1: {
    id: 1,
    sender_email: 'john.doe@example.com',
    received_date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    subject: 'Invoice Documents',
    folder_name: 'Inbox',
  },
  2: {
    id: 2,
    sender_email: 'jane.smith@acme.com',
    received_date: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    subject: 'Monthly Reports',
    folder_name: 'Inbox',
  },
  3: {
    id: 3,
    sender_email: 'accounting@vendor.com',
    received_date: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    subject: 'RE: Payment Documents',
    folder_name: 'Archive',
  },
};

/**
 * Mock Email API implementation
 */
export const useMockEmailApi = {
  /**
   * Get email data by ID
   */
  getEmailById: async (emailId: number): Promise<EmailData | null> => {
    await new Promise((resolve) => setTimeout(resolve, 50)); // Simulate network delay

    return mockEmails[emailId] || null;
  },
};

export default useMockEmailApi;
