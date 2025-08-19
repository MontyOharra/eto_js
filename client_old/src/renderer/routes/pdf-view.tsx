import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useMemo, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import PdfFieldSelector from "../components/PdfFieldSelector";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import PdfObjectOverlay from "../components/PdfTextBoxOverlay";
import type { PdfObject } from "../../@types/global";

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

interface Box {
  id: number;
  left: number;
  top: number;
  right: number;
  bottom: number;
}

interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

const DESIRED_WIDTH = 800; // Base width before zooming

function PdfViewer() {
  const { file } = Route.useSearch();
  const [numPages, setNumPages] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  // Zoom state (1 = 100%)
  const [zoom, setZoom] = useState(1);
  const desiredWidth = DESIRED_WIDTH * zoom;

  const [pdfDoc, setPdfDoc] = useState<pdfjs.PDFDocumentProxy | null>(null);

  // For mouse coordinate mapping
  const pageContainerRef = useRef<HTMLDivElement>(null);
  const [viewInfo, setViewInfo] = useState<{
    scale: number;
    height: number;
  } | null>(null);
  const [mousePos, setMousePos] = useState<{
    x: number;
    y: number;
    pdfX: number;
    pdfY: number;
  } | null>(null);

  // Store PDF objects from Python extraction
  const [allPdfObjects, setAllPdfObjects] = useState<PdfObject[]>([]);
  const [currentPageObjects, setCurrentPageObjects] = useState<PdfObject[]>([]);

  // toggles
  const [showRawBoxes, setShowRawBoxes] = useState(false);

  // Track boxes for each page number
  const [boxesPerPage, setBoxesPerPage] = useState<Record<number, Box[]>>({});

  const [pdfData, setPdfData] = useState<Uint8Array | null>(null);

  // Memoize the current page boxes to avoid creating new empty arrays
  const currentPageBoxes = useMemo(() => {
    return boxesPerPage[page] || [];
  }, [boxesPerPage, page]);

  // Load the PDF binary via IPC once on mount
  useEffect(() => {
    (async () => {
      try {
        const bytes = await window.electron.readPdfFile(decodedPath);
        // Create a defensive copy so React-PDF always receives the same
        // buffer instance and to avoid detached-buffer warnings.
        setPdfData(new Uint8Array(bytes));

        // Extract PDF objects using Python script
        const objects = await window.electron.extractPdfObjects(decodedPath);
        setAllPdfObjects(objects);
      } catch (err) {
        console.error("Failed to load PDF data or extract objects", err);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onLoadSuccess = (doc: pdfjs.PDFDocumentProxy) => {
    setNumPages(doc.numPages);
    setPdfDoc(doc);
  };

  const nextPage = () => setPage((p) => Math.min(numPages ?? p, p + 1));
  const prevPage = () => setPage((p) => Math.max(1, p - 1));

  const handleBoxesChange = (updated: Box[]) => {
    setBoxesPerPage((prev) => ({ ...prev, [page]: updated }));
  };

  const handleSaveClick = () => {
    // Consolidate all boxes across pages and log
    console.log("Saved field boxes:", boxesPerPage);
  };

  // Update current page objects and transform coordinates when page or document changes
  useEffect(() => {
    if (!pdfDoc || allPdfObjects.length === 0) return;

    (async () => {
      try {
        const pdfPage = await pdfDoc.getPage(page);
        // The <Page> component renders at desired width, so calculate scale
        const unscaledViewport = pdfPage.getViewport({ scale: 1 });
        const scale = desiredWidth / unscaledViewport.width;
        const viewport = pdfPage.getViewport({ scale });

        // Store scale & viewport height for mouse mapping
        setViewInfo({ scale, height: viewport.height });

        // Filter objects for current page (pages are 0-indexed in Python, 1-indexed in React)
        const pageObjects = allPdfObjects.filter(
          (obj) => obj.page === page - 1
        );

        // Transform coordinates from PDF space to screen space
        const transformedObjects = pageObjects.map((obj) => {
          const [x0, y0, x1, y1] = obj.bbox;
          // Transform coordinates: scale and flip Y axis
          const screenX0 = x0 * scale;
          const screenX1 = x1 * scale;
          const screenY0 = viewport.height - y1 * scale;
          const screenY1 = viewport.height - y0 * scale;

          return {
            ...obj,
            bbox: [screenX0, screenY0, screenX1, screenY1] as [
              number,
              number,
              number,
              number,
            ],
          };
        });

        setCurrentPageObjects(transformedObjects);
      } catch (err) {
        console.error("Failed to transform PDF objects", err);
      }
    })();
  }, [pdfDoc, page, desiredWidth, allPdfObjects]);

  // Convert PDF objects to text rects for field selector compatibility
  const textRects = useMemo(() => {
    return currentPageObjects
      .filter((obj) => obj.type === "word" || obj.type === "text_line")
      .map((obj) => {
        const [x0, y0, x1, y1] = obj.bbox;
        return {
          left: x0,
          top: y0,
          width: x1 - x0,
          height: y1 - y0,
        };
      });
  }, [currentPageObjects]);

  // Mouse move handler to compute PDF-space coords
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!pageContainerRef.current || !viewInfo) return;
    const rect = pageContainerRef.current.getBoundingClientRect();
    const relX = e.clientX - rect.left;
    const relY = e.clientY - rect.top;

    const pdfX = relX / viewInfo.scale;
    const pdfY = relY / viewInfo.scale; // measure Y from top now

    setMousePos({ x: relX, y: relY, pdfX, pdfY });
  };

  const handleMouseLeave = () => setMousePos(null);

  // Build a proper file:// URL from the `file` query param.
  const decodedPath = decodeURIComponent(file);

  // Provide pdf.js with a fresh Uint8Array copy; avoids 'detached buffer'
  const fileSource = useMemo(() => {
    if (!pdfData) return undefined;
    return { data: new Uint8Array(pdfData) }; // copy
  }, [pdfData]);

  return (
    <main className="min-h-screen bg-gray-100 flex flex-col items-center p-8 overflow-hidden">
      {/* Control bar */}
      <div className="flex gap-4 mb-4 z-10">
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

        <button
          onClick={handleSaveClick}
          className="px-4 py-2 bg-green-600 text-white rounded"
        >
          Save
        </button>

        <label className="flex items-center gap-1 text-sm ml-4">
          <input
            type="checkbox"
            checked={showRawBoxes}
            onChange={(e) => setShowRawBoxes(e.target.checked)}
          />
          Show Objects
        </label>
      </div>

      {/* Zoom slider on the left */}
      <div className="fixed left-4 top-1/2 -translate-y-1/2 -rotate-90 z-20">
        <input
          type="range"
          min="0.5"
          max="2"
          step="0.1"
          value={zoom}
          onChange={(e) => setZoom(parseFloat(e.target.value))}
          className="w-40"
        />
      </div>

      <div className="w-full max-w-4xl overflow-y-auto bg-white relative">
        {fileSource && (
          <>
            <div
              ref={pageContainerRef}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
              className="relative inline-block"
            >
              <Document file={fileSource} onLoadSuccess={onLoadSuccess}>
                <Page
                  pageNumber={page}
                  renderTextLayer
                  renderAnnotationLayer
                  width={desiredWidth}
                />
              </Document>
              {/* PDF Field Selector overlay */}
              <PdfFieldSelector
                key={page}
                initialBoxes={currentPageBoxes}
                onBoxesChange={handleBoxesChange}
                textRects={textRects}
              />
              {/* PDF Objects overlay */}
              {showRawBoxes && (
                <PdfObjectOverlay objects={currentPageObjects} />
              )}
            </div>
            {/* Mouse position display */}
            {mousePos && (
              <div className="absolute top-2 right-2 bg-white/80 text-xs px-2 py-0.5 rounded shadow">
                {mousePos.pdfX.toFixed(1)}, {mousePos.pdfY.toFixed(1)}
              </div>
            )}
          </>
        )}
      </div>

      <p className="fixed bottom-4 text-sm text-gray-600 bg-white/80 px-2 py-1 rounded shadow z-20">
        Page {page} {numPages ? `of ${numPages}` : ""}
      </p>
    </main>
  );
}
