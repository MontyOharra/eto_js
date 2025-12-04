/**
 * PDF Subset Creation Utility
 * Creates a new PDF containing only selected pages from an original PDF
 */

import { PDFDocument } from 'pdf-lib';

/**
 * Creates a subset PDF containing only the selected pages
 *
 * @param originalPdfFile - The original PDF file
 * @param selectedPages - Array of page indices to include (0-indexed)
 * @returns New File object containing only the selected pages (renumbered 1, 2, 3...)
 * @throws Error if PDF creation fails
 *
 * @example
 * const original = new File([...], 'document.pdf');
 * const subset = await createSubsetPdf(original, [2, 4, 5]); // Extract pages 3, 5, 6
 * // subset now has 3 pages numbered 1, 2, 3
 */
export async function createSubsetPdf(
  originalPdfFile: File,
  selectedPages: number[]
): Promise<File> {
  try {
    // Read original PDF file as ArrayBuffer
    const originalBytes = await originalPdfFile.arrayBuffer();

    // Load the original PDF
    const originalPdf = await PDFDocument.load(originalBytes);

    // Create a new PDF document
    const newPdf = await PDFDocument.create();

    // Copy selected pages to new PDF
    // selectedPages are 0-indexed, but PDFDocument uses 0-indexed internally too
    console.log('[createSubsetPdf] Copying pages:', selectedPages, 'from PDF with', originalPdf.getPageCount(), 'pages');
    const copiedPages = await newPdf.copyPages(originalPdf, selectedPages);

    // Add each copied page to the new document
    for (const page of copiedPages) {
      newPdf.addPage(page);
    }

    // Save the new PDF as bytes
    const newPdfBytes = await newPdf.save();

    // Create a new File object from the bytes
    // Use random filename since this is a temporary file that will be uploaded immediately
    const randomId = Math.random().toString(36).substring(2, 15);
    const timestamp = Date.now();
    const subsetFileName = `template_${timestamp}_${randomId}.pdf`;

    const subsetFile = new File([new Uint8Array(newPdfBytes)], subsetFileName, {
      type: 'application/pdf',
      lastModified: Date.now(),
    });

    console.log(
      `[createSubsetPdf] Created subset PDF with ${copiedPages.length} pages (indices: ${selectedPages.join(', ')})`
    );

    return subsetFile;
  } catch (error) {
    console.error('[createSubsetPdf] Failed to create subset PDF:', error);
    throw new Error(
      `Failed to create subset PDF: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}
