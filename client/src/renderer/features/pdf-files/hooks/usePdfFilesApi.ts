/**
 * PDF Files API Hook
 * Real API implementation for PDF file processing endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import { PdfProcessResponseDTO, PdfFileMetadataDTO, PdfObjectsResponseDTO } from '../api/types';

export function usePdfFilesApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = API_CONFIG.ENDPOINTS.PDF_FILES;

  /**
   * Helper to handle API calls with loading and error states
   */
  const withLoadingAndError = useCallback(
    async <T,>(apiCall: () => Promise<T>): Promise<T> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiCall();
        return result;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * POST /api/pdf-files/process-objects
   * Process uploaded PDF and extract objects (no persistence)
   * Used during template creation wizard
   */
  const processObjects = useCallback(
    async (pdfFile: File): Promise<PdfProcessResponseDTO> => {
      return withLoadingAndError(async () => {
        const formData = new FormData();
        formData.append('pdf_file', pdfFile);

        const response = await apiClient.post<PdfProcessResponseDTO>(
          `${baseUrl}/process-objects`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        );

        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/pdf-files/{id}
   * Get PDF file metadata
   */
  const getPdfMetadata = useCallback(
    async (pdfFileId: number): Promise<PdfFileMetadataDTO> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<PdfFileMetadataDTO>(
          `${baseUrl}/${pdfFileId}`
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/pdf-files/{id}/objects
   * Get extracted PDF objects for stored PDF
   */
  const getPdfObjects = useCallback(
    async (pdfFileId: number, objectType?: string): Promise<PdfObjectsResponseDTO> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<PdfObjectsResponseDTO>(
          `${baseUrl}/${pdfFileId}/objects`,
          {
            params: objectType ? { object_type: objectType } : undefined,
          }
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/pdf-files/{id}/download
   * Get PDF download URL
   */
  const getPdfDownloadUrl = useCallback(
    (pdfFileId: number): string => {
      return `${API_CONFIG.BASE_URL}${baseUrl}/${pdfFileId}/download`;
    },
    [baseUrl]
  );

  return {
    // State
    isLoading,
    error,

    // API methods
    processObjects,
    getPdfMetadata,
    getPdfObjects,
    getPdfDownloadUrl,
  };
}
