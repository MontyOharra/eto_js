/**
 * PDF API Hooks
 * TanStack Query hooks for PDF file operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import { PdfFileMetadata, PdfObjectsResponse, PdfProcessResponse } from './types';

const baseUrl = API_CONFIG.ENDPOINTS.PDF_FILES;

// ============================================================================
// Query Hooks (GET operations)
// ============================================================================

/**
 * Combined hook - fetches PDF metadata, objects, and download URL in parallel
 * Convenient for components that need all PDF data at once
 */
export interface PdfData {
  objectsData: PdfObjectsResponse;
  url: string;
  metadata: PdfFileMetadata;
}

export function usePdfData(pdfFileId: number | null, pages?: number[]) {
  return useQuery({
    queryKey: ['pdf', pdfFileId, pages],
    queryFn: async (): Promise<PdfData> => {
      if (!pdfFileId) {
        throw new Error('No PDF file ID provided');
      }

      // Fetch PDF objects and metadata in parallel
      const [objectsData, metadata] = await Promise.all([
        apiClient.get<PdfObjectsResponse>(
          `${baseUrl}/${pdfFileId}/objects`,
          {
            params: pages ? { pages } : undefined,
          }
        ).then(res => res.data),
        apiClient.get<PdfFileMetadata>(`${baseUrl}/${pdfFileId}`).then(res => res.data),
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

/**
 * Fetch PDF file metadata only
 * Use when you only need file info, not extracted objects
 */
export function usePdfMetadata(pdfFileId: number | null) {
  return useQuery({
    queryKey: ['pdf', 'metadata', pdfFileId],
    queryFn: async (): Promise<PdfFileMetadata> => {
      if (!pdfFileId) {
        throw new Error('No PDF file ID provided');
      }

      const response = await apiClient.get<PdfFileMetadata>(
        `${baseUrl}/${pdfFileId}`
      );
      return response.data;
    },
    enabled: !!pdfFileId,
    staleTime: Infinity, // PDF metadata never changes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });
}

/**
 * Fetch extracted PDF objects only
 * Use when you only need extracted objects, not metadata
 */
export function usePdfObjects(
  pdfFileId: number | null,
  objectType?: string,
  pages?: number[]
) {
  return useQuery({
    queryKey: ['pdf', 'objects', pdfFileId, objectType, pages],
    queryFn: async (): Promise<PdfObjectsResponse> => {
      if (!pdfFileId) {
        throw new Error('No PDF file ID provided');
      }

      const response = await apiClient.get<PdfObjectsResponse>(
        `${baseUrl}/${pdfFileId}/objects`,
        {
          params: {
            ...(objectType ? { object_type: objectType } : {}),
            ...(pages ? { pages } : {}),
          },
        }
      );
      return response.data;
    },
    enabled: !!pdfFileId,
    staleTime: Infinity, // PDF objects never change
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });
}

// ============================================================================
// Mutation Hooks (POST operations)
// ============================================================================

/**
 * Upload and store PDF file with automatic object extraction
 * Returns stored PDF metadata with ID
 */
export function useUploadPdf() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (pdfFile: File): Promise<PdfFileMetadata> => {
      const formData = new FormData();
      formData.append('pdf_file', pdfFile);

      const response = await apiClient.post<PdfFileMetadata>(
        baseUrl,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      return response.data;
    },
    onSuccess: (data) => {
      // Cache the uploaded PDF's metadata
      queryClient.setQueryData(['pdf', 'metadata', data.id], data);
    },
  });
}

/**
 * Process uploaded PDF and extract objects without persistence
 * Used during template creation wizard for temporary object extraction
 */
export function useProcessPdfObjects() {
  return useMutation({
    mutationFn: async ({ pdfFile, pages }: { pdfFile: File; pages?: number[] }): Promise<PdfProcessResponse> => {
      if (!pdfFile) {
        throw new Error('PDF file is required');
      }

      const formData = new FormData();
      formData.append('pdf_file', pdfFile);

      const response = await apiClient.post<PdfProcessResponse>(
        `${baseUrl}/process-objects`,
        formData,
        {
          params: pages ? { pages } : undefined,
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      return response.data;
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get PDF download URL for a given PDF file ID
 * No API call needed - just constructs the URL
 */
export function getPdfDownloadUrl(pdfFileId: number): string {
  return `${API_CONFIG.BASE_URL}${baseUrl}/${pdfFileId}/download`;
}
