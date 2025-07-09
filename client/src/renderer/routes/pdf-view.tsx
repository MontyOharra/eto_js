import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useMemo } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import PdfFieldSelector from "../components/PdfFieldSelector";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

export const Route = createFileRoute("/pdf-view")({
  validateSearch: (search) => {
    if (!search.file || typeof search.file !== "string") {
      throw new Error("'file' query parameter is required");
    }
    return { file: search.file } as const;
  },
  component: PdfViewer,
});

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

function PdfViewer() {
  const { file } = Route.useSearch();
  const [numPages, setNumPages] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const [pdfData, setPdfData] = useState<Uint8Array | null>(null);

  // Load the PDF binary via IPC once on mount
  useEffect(() => {
    (async () => {
      try {
        const bytes = await window.electron.readPdfFile(decodedPath);
        // Create a defensive copy so React-PDF always receives the same
        // buffer instance and to avoid detached-buffer warnings.
        setPdfData(new Uint8Array(bytes));
      } catch (err) {
        console.error("Failed to load PDF data", err);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  const nextPage = () => setPage((p) => Math.min(numPages ?? p, p + 1));
  const prevPage = () => setPage((p) => Math.max(1, p - 1));

  // Build a proper file:// URL from the `file` query param.
  const decodedPath = decodeURIComponent(file);

  // Provide pdf.js with a fresh Uint8Array copy; avoids 'detached buffer'
  const fileSource = useMemo(() => {
    if (!pdfData) return undefined;
    return { data: new Uint8Array(pdfData) }; // copy
  }, [pdfData]);

  return (
    <main className="min-h-screen bg-gray-100 flex flex-col items-center p-8">
      <div className="flex gap-4 mb-4">
        <button
          onClick={prevPage}
          disabled={page === 1}
          className="px-4 py-2 bg-indigo-600 text-white rounded disabled:bg-gray-400"
        >
          Prev
        </button>
        <button
          onClick={nextPage}
          disabled={numPages ? page >= numPages : true}
          className="px-4 py-2 bg-indigo-600 text-white rounded disabled:bg-gray-400"
        >
          Next
        </button>
      </div>

      <div className="w-full max-w-4xl overflow-y-auto border rounded-2xl bg-black p-4 relative">
        {fileSource && (
          <>
            <div className="relative inline-block border-4 border-lime-500">
              <Document file={fileSource} onLoadSuccess={onLoadSuccess}>
                <Page
                  pageNumber={page}
                  renderTextLayer
                  renderAnnotationLayer
                  width={800}
                />
              </Document>
              {/* overlay on top */}
              <PdfFieldSelector />
            </div>
          </>
        )}
      </div>

      <p className="mt-2 text-sm text-gray-600">
        Page {page} {numPages ? `of ${numPages}` : ""}
      </p>
    </main>
  );
}
