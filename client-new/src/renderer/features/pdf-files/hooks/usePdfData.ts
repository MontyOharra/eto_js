/**
 * usePdfData
 * React Query hook for fetching and caching PDF data
 * Prevents unnecessary reloads when components unmount/remount
 */

import { useQuery } from '@tanstack/react-query';
import { useMockPdfApi } from '../mocks/useMockPdfApi';

export interface PdfData {
  objectsData: any;
  url: string;
}

export function usePdfData(pdfFileId: number | null) {
  return useQuery({
    queryKey: ['pdf', pdfFileId],
    queryFn: async (): Promise<PdfData> => {
      if (!pdfFileId) {
        throw new Error('No PDF file ID provided');
      }

      console.log('[usePdfData] Fetching PDF data for ID:', pdfFileId);

      const objectsData = await useMockPdfApi.getPdfObjects(pdfFileId);
      const url = useMockPdfApi.getPdfDownloadUrl(pdfFileId);

      console.log('[usePdfData] PDF data fetched successfully');

      return { objectsData, url };
    },
    enabled: !!pdfFileId, // Only run query if pdfFileId exists
    staleTime: Infinity, // Never refetch (perfect for static PDFs)
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes after last use
  });
}
