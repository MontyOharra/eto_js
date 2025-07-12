import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useMemo, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import PdfFieldSelector from "../components/PdfFieldSelector";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { decodeOperatorList, extractShowTextRuns } from "../helpers/pdfDebug";
import TextRunOverlay from "../components/TextRunOverlay";
import PdfTextBoxOverlay from "../components/PdfTextBoxOverlay";

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

  const [textRunRects, setTextRunRects] = useState<Rect[]>([]);
  const [rawTextRects, setRawTextRects] = useState<Rect[]>([]);

  // toggles
  const [showRunBoxes, setShowRunBoxes] = useState(false);
  const [showRawBoxes, setShowRawBoxes] = useState(false);

  // Track boxes for each page number
  const [boxesPerPage, setBoxesPerPage] = useState<Record<number, Box[]>>({});

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

  // Extract text bounding boxes whenever page or document changes
  useEffect(() => {
    if (!pdfDoc) return;

    (async () => {
      try {
        const pdfPage = await pdfDoc.getPage(page);
        // The <Page> component renders at width 800, so mirror that scale
        const unscaledViewport = pdfPage.getViewport({ scale: 1 });

        const scale = desiredWidth / unscaledViewport.width;
        const viewport = pdfPage.getViewport({ scale });
        // Store scale & viewport height for mouse mapping
        setViewInfo({ scale, height: viewport.height });
        // --- Raw textContent rectangles (toggleable) ---
        try {
          const textContent = await pdfPage.getTextContent();
          const rects: Rect[] = (
            textContent.items as Array<{
              transform: number[];
              width: number;
              height: number;
            }>
          )
            .map((item) => {
              const [, , , , x, y] = item.transform as number[];
              const widthPt = item.width;
              const heightPt = item.height;
              const left = x * scale;
              const width = widthPt * scale;
              const height = heightPt * scale;
              const top = viewport.height - y * scale - height;
              return { left, top, width, height };
            })
            .filter((rect) => rect.height > 0);
          setRawTextRects(rects);
        } catch (e) {
          console.warn("Failed to get textContent boxes", e);
        }
      } catch (err) {
        console.error("Failed to extract text boxes", err);
      }
    })();
  }, [pdfDoc, page, desiredWidth]);

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

  // const combinedBoxes = useMemo(
  //   () => [...textBoxes, ...imageBoxes],
  //   [textBoxes, imageBoxes]
  // );

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
          Raw boxes
        </label>

        <label className="flex items-center gap-1 text-sm ml-2">
          <input
            type="checkbox"
            checked={showRunBoxes}
            onChange={(e) => setShowRunBoxes(e.target.checked)}
          />
          Run boxes
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
              {/* Mouse overlay removed to clean up per requirement */}
              {/* debug overlay – highlight text and image objects */}
              {showRawBoxes && <PdfTextBoxOverlay boxes={rawTextRects} />}
              {showRunBoxes && <TextRunOverlay boxes={textRunRects} />}
              {/* overlay for user selections */}
              <PdfFieldSelector
                key={page}
                initialBoxes={boxesPerPage[page] ?? []}
                onBoxesChange={handleBoxesChange}
              />
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
