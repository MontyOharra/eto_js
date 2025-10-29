/**
 * usePdfData
 * React Query hook for fetching and caching PDF data
 * Prevents unnecessary reloads when components unmount/remount
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import { PdfFileMetadataDTO, PdfObjectsResponseDTO } from '../api/types';

export interface PdfData {
  objectsData: PdfObjectsResponseDTO;
  url: string;
  metadata: PdfFileMetadataDTO;
}

export function usePdfData(pdfFileId: number | null) {
  const baseUrl = API_CONFIG.ENDPOINTS.PDF_FILES;

  return useQuery({
    queryKey: ['pdf', pdfFileId],
    queryFn: async (): Promise<PdfData> => {
      if (!pdfFileId) {
        throw new Error('No PDF file ID provided');
      }

      // Fetch PDF objects and metadata in parallel
      const [objectsData, metadata] = await Promise.all([
        apiClient.get<PdfObjectsResponseDTO>(`${baseUrl}/${pdfFileId}/objects`).then(res => res.data),
        apiClient.get<PdfFileMetadataDTO>(`${baseUrl}/${pdfFileId}`).then(res => res.data),
      ]);

      // Construct download URL
      const url = `${API_CONFIG.BASE_URL}${baseUrl}/${pdfFileId}/download`;

      return { objectsData, url, metadata };
    },
    enabled: !!pdfFileId, // Only run query if pdfFileId exists
    staleTime: Infinity, // Never refetch (perfect for static PDFs)
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes after last use
  });
}
