/**
 * usePdfData
 * React Query hook for fetching and caching PDF data
 * Prevents unnecessary reloads when components unmount/remount
 */

import { useQuery } from '@tanstack/react-query';
import { useMockPdfApi } from '../mocks/useMockPdfApi';
import { PdfFileMetadataDTO } from '../api/types';
import { useMockEmailApi, EmailData } from '../../emails/mocks/useMockEmailApi';

export interface PdfData {
  objectsData: any;
  url: string;
  metadata: PdfFileMetadataDTO;
  emailData?: EmailData | null;
}

export function usePdfData(pdfFileId: number | null) {
  return useQuery({
    queryKey: ['pdf', pdfFileId],
    queryFn: async (): Promise<PdfData> => {
      if (!pdfFileId) {
        throw new Error('No PDF file ID provided');
      }

      console.log('[usePdfData] Fetching PDF data for ID:', pdfFileId);

      const [objectsData, metadata] = await Promise.all([
        useMockPdfApi.getPdfObjects(pdfFileId),
        useMockPdfApi.getPdfMetadata(pdfFileId),
      ]);
      const url = useMockPdfApi.getPdfDownloadUrl(pdfFileId);

      // Fetch email data if PDF has an associated email
      let emailData: EmailData | null = null;
      if (metadata.email_id !== null) {
        emailData = await useMockEmailApi.getEmailById(metadata.email_id);
      }

      console.log('[usePdfData] PDF data fetched successfully');

      return { objectsData, url, metadata, emailData };
    },
    enabled: !!pdfFileId, // Only run query if pdfFileId exists
    staleTime: Infinity, // Never refetch (perfect for static PDFs)
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes after last use
  });
}
