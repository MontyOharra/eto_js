import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
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

  const onLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  const nextPage = () => setPage((p) => Math.min(numPages ?? p, p + 1));
  const prevPage = () => setPage((p) => Math.max(1, p - 1));

  // The file path is URL-encoded; decode it then turn into a proper file URL.
  const decodedPath = decodeURIComponent(file);
  const normalizeForUrl = (p: string) => {
    // Replace backslashes with forward slashes for Windows and ensure leading slash after drive letter.
    const withSlashes = p.replace(/\\/g, "/");
    if (/^[a-zA-Z]:\//.test(withSlashes)) {
      return `/` + withSlashes; // adds leading slash before drive letter
    }
    return withSlashes;
  };

  const fileUrl = "C:/HTC_EmailToParse%20-%20Copy/Mwb%2093195628%20-%20Delivery%20Receipt%20(Plain).pdf";

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

      <div className="w-full max-w-4xl overflow-y-auto border rounded-2xl shadow-inner bg-white p-4">
        <Document file={fileUrl} onLoadSuccess={onLoadSuccess}>
          <Page
            pageNumber={page}
            renderTextLayer
            renderAnnotationLayer
            width={800}
          />
        </Document>
      </div>

      <p className="mt-2 text-sm text-gray-600">
        Page {page} {numPages ? `of ${numPages}` : ""}
      </p>
    </main>
  );
}
