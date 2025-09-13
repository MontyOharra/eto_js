import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { apiClient } from "../../services/api";

export const Route = createFileRoute("/dashboard/emails")({
  component: EmailsPage,
});

interface ProcessedEmail {
  id: number;
  message_id: string;
  subject: string;
  sender_email: string;
  sender_name?: string;
  received_date: string;
  folder_name: string;
  has_attachments: boolean;
  attachment_count: number;
  created_at: string;
}

interface EmailsResponse {
  success: boolean;
  data: ProcessedEmail[];
  total: number;
}

function EmailsPage() {
  const [emails, setEmails] = useState<ProcessedEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalEmails, setTotalEmails] = useState(0);
  const limit = 50;

  const fetchEmails = async (pageNum: number = 1) => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await apiClient.getProcessedEmails({
        page: pageNum,
        limit: limit
      });
      
      if (result.success) {
        setEmails(result.data);
        setTotalEmails(result.total);
      } else {
        throw new Error('Failed to fetch emails');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmails(page);
  }, [page]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const totalPages = Math.ceil(totalEmails / limit);

  if (loading && emails.length === 0) {
    return (
      <div className="flex-1 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-blue-300 mb-2">
            Processed Emails
          </h1>
          <p className="text-gray-400">
            View emails that have been processed by the email ingestion service
          </p>
        </div>
        
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading emails...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-blue-300 mb-2">
              Processed Emails
            </h1>
            <p className="text-gray-400">
              View emails that have been processed by the email ingestion service
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => fetchEmails(page)}
              disabled={loading}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-sm rounded transition-colors"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
        
        {totalEmails > 0 && (
          <p className="text-xs text-gray-500 mt-2">
            Showing {emails.length} of {totalEmails} emails
          </p>
        )}
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 mb-6">
          <div className="flex items-center">
            <svg className="w-6 h-6 text-red-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-red-400 font-medium">Failed to load emails</h3>
              <p className="text-gray-400 text-sm mt-1">{error}</p>
            </div>
          </div>
          <button 
            onClick={() => fetchEmails(page)}
            className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors"
          >
            Try Again
          </button>
        </div>
      )}

      {emails.length === 0 && !loading && !error && (
        <div className="text-center py-12">
          <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <h3 className="text-gray-400 text-lg font-medium mb-2">No emails found</h3>
          <p className="text-gray-500">No emails have been processed yet by the email ingestion service.</p>
        </div>
      )}

      {emails.length > 0 && (
        <>
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Subject
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      From
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Folder
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Received
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Attachments
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Processed
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {emails.map((email) => (
                    <tr key={email.id} className="hover:bg-gray-700/50">
                      <td className="px-6 py-4">
                        <div className="text-sm text-white font-medium truncate max-w-xs" title={email.subject}>
                          {email.subject}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          ID: {email.message_id.substring(0, 20)}...
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-white">{email.sender_email}</div>
                        {email.sender_name && (
                          <div className="text-xs text-gray-400">{email.sender_name}</div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-700 text-gray-300">
                          {email.folder_name}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">
                        {formatDate(email.received_date)}
                      </td>
                      <td className="px-6 py-4">
                        {email.has_attachments ? (
                          <div className="flex items-center">
                            <svg className="w-4 h-4 text-green-400 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                            <span className="text-sm text-green-400">{email.attachment_count}</span>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-500">None</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">
                        {formatDate(email.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <div className="text-sm text-gray-400">
                Page {page} of {totalPages}
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1 || loading}
                  className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-white text-sm rounded transition-colors"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages || loading}
                  className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-white text-sm rounded transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}