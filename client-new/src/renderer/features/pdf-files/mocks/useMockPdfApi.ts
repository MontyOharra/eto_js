/**
 * Mock PDF Files API
 * Returns real extracted PDF object data from test PDFs
 */

import { PdfFileMetadataDTO, PdfObjectsResponseDTO } from '../api/types';

// Import extracted PDF object data
import pdf2Objects from './data/2_objects.json';
import pdf3Objects from './data/3_objects.json';
import pdf4Objects from './data/4_objects.json';
import pdf103Objects from './data/103_objects.json';

/**
 * Mock PDF file metadata database
 */
const mockPdfMetadata: Record<number, PdfFileMetadataDTO> = {
  2: {
    id: 2,
    email_id: null,
    filename: '2.pdf',
    original_filename: '2.pdf',
    relative_path: 'pdfs/2.pdf',
    file_size: 145632,
    file_hash: '84cb9aba3a6850e6a1b2c3d4e5f6g7h8',
    page_count: 2,
  },
  3: {
    id: 3,
    email_id: null,
    filename: '3.pdf',
    original_filename: '3.pdf',
    relative_path: 'pdfs/3.pdf',
    file_size: 148923,
    file_hash: '23f4ebf74c9ac2dea1b2c3d4e5f6g7h8',
    page_count: 2,
  },
  4: {
    id: 4,
    email_id: null,
    filename: '4.pdf',
    original_filename: '4.pdf',
    relative_path: 'pdfs/4.pdf',
    file_size: 892456,
    file_hash: 'f44883a1902019f3a1b2c3d4e5f6g7h8',
    page_count: 18,
  },
  103: {
    id: 103,
    email_id: null,
    filename: '103.pdf',
    original_filename: '103.pdf',
    relative_path: 'pdfs/103.pdf',
    file_size: 567834,
    file_hash: 'c81e4be87fde4e6fa1b2c3d4e5f6g7h8',
    page_count: 11,
  },
};

/**
 * Mock PDF objects database (real extracted data)
 */
const mockPdfObjects: Record<number, PdfObjectsResponseDTO> = {
  2: pdf2Objects as PdfObjectsResponseDTO,
  3: pdf3Objects as PdfObjectsResponseDTO,
  4: pdf4Objects as PdfObjectsResponseDTO,
  103: pdf103Objects as PdfObjectsResponseDTO,
};

/**
 * Mock PDF Files API implementation
 */
export const useMockPdfApi = {
  /**
   * Get PDF file metadata
   * Endpoint: GET /pdf-files/{id}
   */
  getPdfMetadata: async (pdfFileId: number): Promise<PdfFileMetadataDTO> => {
    await new Promise((resolve) => setTimeout(resolve, 100)); // Simulate network delay

    const metadata = mockPdfMetadata[pdfFileId];
    if (!metadata) {
      throw new Error(`PDF file ${pdfFileId} not found`);
    }

    return metadata;
  },

  /**
   * Get PDF download URL
   * Endpoint: GET /pdf-files/{id}/download
   * Returns URL to PDF file in public directory
   */
  getPdfDownloadUrl: (pdfFileId: number): string => {
    // Check if PDF exists in mock data
    if (!mockPdfMetadata[pdfFileId]) {
      throw new Error(`PDF file ${pdfFileId} not found`);
    }

    // Return URL to PDF in public directory (served by Vite dev server)
    return `/data/pdfs/${pdfFileId}.pdf`;
  },

  /**
   * Get extracted PDF objects
   * Endpoint: GET /pdf-files/{id}/objects
   * Returns REAL extracted data from test PDFs
   */
  getPdfObjects: async (
    pdfFileId: number
  ): Promise<PdfObjectsResponseDTO> => {
    await new Promise((resolve) => setTimeout(resolve, 200)); // Simulate network delay

    const objects = mockPdfObjects[pdfFileId];
    if (!objects) {
      throw new Error(`PDF objects for file ${pdfFileId} not found`);
    }

    console.log(
      `[Mock API] Returning PDF objects for ID ${pdfFileId}:`,
      {
        page_count: objects.page_count,
        text_words: objects.objects.text_words.length,
        text_lines: objects.objects.text_lines.length,
        graphic_rects: objects.objects.graphic_rects.length,
        graphic_lines: objects.objects.graphic_lines.length,
        graphic_curves: objects.objects.graphic_curves.length,
        images: objects.objects.images.length,
        tables: objects.objects.tables.length,
      }
    );

    return objects;
  },

  /**
   * Get list of available test PDFs
   */
  getAvailablePdfIds: (): number[] => {
    return Object.keys(mockPdfMetadata).map(Number).sort();
  },
};

export default useMockPdfApi;
