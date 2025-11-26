/**
 * PdfViewerPanel
 * PDF viewer with optional extraction field overlay
 * Handles PDF URL generation and auto-fit during resize
 */

import { useEffect, useRef } from "react";
import { PdfViewer, usePdfViewer } from "../../../pdf";
import { getPdfDownloadUrl } from "../../../pdf/api/hooks";
import { ExtractedFieldsOverlay } from "./ExtractedFieldsOverlay";
import type { ExtractionResult } from "../../types";

interface PdfViewerPanelProps {
  pdfFileId: number;
  overlayFields?: ExtractionResult[];
  isDragging?: boolean;
}

// Helper component to trigger fit-to-width on resize (only during divider drag)
function AutoFitOnResize({ isDragging }: { isDragging: boolean }) {
  const { fitToWidth, pdfDimensions } = usePdfViewer();
  const pdfViewerRef = useRef<HTMLDivElement>(null);
  const hasAutoFittedOnLoad = useRef(false);

  // Auto-fit when PDF first loads
  useEffect(() => {
    if (
      !pdfDimensions ||
      !pdfViewerRef.current ||
      hasAutoFittedOnLoad.current
    ) {
      return;
    }

    const pdfViewerContainer = pdfViewerRef.current.parentElement;
    if (!pdfViewerContainer) {
      return;
    }

    // Trigger fit-to-width on initial load
    const containerWidth = pdfViewerContainer.clientWidth;
    const sidebarWidth = 64; // w-16 = 64px
    fitToWidth(containerWidth, sidebarWidth);
    hasAutoFittedOnLoad.current = true;
  }, [pdfDimensions, fitToWidth]);

  // Trigger fit-to-width on resize, but ONLY when dragging the divider
  useEffect(() => {
    if (!isDragging || !pdfViewerRef.current || !pdfDimensions) {
      return;
    }

    // Get the actual PdfViewer container (same element the fit button measures)
    const pdfViewerContainer = pdfViewerRef.current.parentElement;
    if (!pdfViewerContainer) {
      return;
    }

    const resizeObserver = new ResizeObserver(() => {
      if (!pdfViewerContainer || !isDragging) {
        return;
      }

      const containerWidth = pdfViewerContainer.clientWidth;
      const sidebarWidth = 64; // w-16 = 64px
      fitToWidth(containerWidth, sidebarWidth);
    });

    resizeObserver.observe(pdfViewerContainer);

    return () => {
      resizeObserver.disconnect();
    };
  }, [fitToWidth, pdfDimensions, isDragging]);

  return <div ref={pdfViewerRef} style={{ display: "none" }} />;
}

export function PdfViewerPanel({
  pdfFileId,
  overlayFields,
  isDragging = false,
}: PdfViewerPanelProps) {
  const pdfUrl = getPdfDownloadUrl(pdfFileId);

  const handlePdfError = (error: Error) => {
    console.error("PDF load error:", error);
  };

  // Transform extraction results to overlay format if provided
  const extractedFieldsForOverlay = overlayFields?.map((result) => ({
    field_id: result.name,
    label: result.description || result.name,
    value: result.extracted_value,
    page: result.page,
    bbox: result.bbox,
  }));

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg h-full overflow-hidden relative pr-4 pl-1 py-4">
      {pdfUrl ? (
        <PdfViewer pdfUrl={pdfUrl} onError={handlePdfError}>
          <AutoFitOnResize isDragging={isDragging} />
          <PdfViewer.Canvas pdfUrl={pdfUrl} onError={handlePdfError}>
            {/* Show extraction field overlay if provided */}
            {extractedFieldsForOverlay && extractedFieldsForOverlay.length > 0 && (
              <ExtractedFieldsOverlay fields={extractedFieldsForOverlay} />
            )}
          </PdfViewer.Canvas>
          <PdfViewer.ControlsSidebar position="right" />
        </PdfViewer>
      ) : (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-400">No PDF available</p>
        </div>
      )}
    </div>
  );
}
