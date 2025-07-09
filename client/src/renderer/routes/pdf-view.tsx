import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useMemo, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import PdfFieldSelector from "../components/PdfFieldSelector";
import PdfTextBoxOverlay from "../components/PdfTextBoxOverlay";
import { findTextItem } from "../helpers/pdfTextUtils";
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

function PdfViewer() {
  const { file } = Route.useSearch();
  const [numPages, setNumPages] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const [pdfDoc, setPdfDoc] = useState<pdfjs.PDFDocumentProxy | null>(null);
  const [textBoxes, setTextBoxes] = useState<Rect[]>([]);
  const [imageBoxes, setImageBoxes] = useState<Rect[]>([]);
  const [showObjects, setShowObjects] = useState<boolean>(true);

  // Ref to the container that holds the rendered PDF page so we can
  // measure DOM elements (e.g. <img> tags) for additional object bounds.
  const pageContainerRef = useRef<HTMLDivElement>(null);

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

  // Extract text bounding boxes whenever page or document changes
  useEffect(() => {
    if (!pdfDoc) return;

    (async () => {
      try {
        const pdfPage = await pdfDoc.getPage(page);
        // The <Page> component renders at width 800, so mirror that scale
        const unscaledViewport = pdfPage.getViewport({ scale: 1 });
        const desiredWidth = 800;
        const scale = desiredWidth / unscaledViewport.width;
        const viewport = pdfPage.getViewport({ scale });

        const textContent = await pdfPage.getTextContent();

        // Convert each text item to screen-space rectangle
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const boxes: Rect[] = (textContent.items as any[]).map((item) => {
          // item.transform: [a, b, c, d, e, f]
          const [, , , , x, y] = item.transform as number[];
          const width = item.width * scale;
          const height = item.height * scale;

          // pdf.js origin is bottom-left; convert to top-left for CSS
          const top = viewport.height - y * scale - height;

          return {
            left: x * scale,
            top,
            width,
            height,
          };
        });

        setTextBoxes(boxes);

        // --- New: extract images via operator list ---
        const imageRects: Rect[] = [];
        try {
          // getOperatorList may not exist depending on build; guard it.
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const opList: any = await (pdfPage as any).getOperatorList?.();
          if (opList) {
            // Util helpers
            const mult = (m1: number[], m2: number[]) => {
              return [
                m1[0] * m2[0] + m1[2] * m2[1],
                m1[1] * m2[0] + m1[3] * m2[1],
                m1[0] * m2[2] + m1[2] * m2[3],
                m1[1] * m2[2] + m1[3] * m2[3],
                m1[0] * m2[4] + m1[2] * m2[5] + m1[4],
                m1[1] * m2[4] + m1[3] * m2[5] + m1[5],
              ];
            };
            const apply = (pt: number[], m: number[]) => {
              return [
                pt[0] * m[0] + pt[1] * m[2] + m[4],
                pt[0] * m[1] + pt[1] * m[3] + m[5],
              ] as const;
            };

            // Constants for operator IDs we care about (taken from pdf.js OPS enum)
            const OPS_SAVE = 10;
            const OPS_RESTORE = 11;
            const OPS_TRANSFORM = 12;
            const OPS_PAINT_IMAGE = 85;
            const OPS_PAINT_INLINE_IMAGE = 86;

            const { fnArray, argsArray } = opList;
            const stack: number[][] = [];
            let ctm = [1, 0, 0, 1, 0, 0];
            for (let i = 0; i < fnArray.length; i++) {
              const fn = fnArray[i];
              const args = argsArray[i] as number[];
              switch (fn) {
                case OPS_SAVE:
                  stack.push([...ctm]);
                  break;
                case OPS_RESTORE:
                  if (stack.length) ctm = stack.pop()!;
                  break;
                case OPS_TRANSFORM:
                  ctm = mult(ctm, args as number[]);
                  break;
                case OPS_PAINT_IMAGE:
                case OPS_PAINT_INLINE_IMAGE: {
                  // The CTM currently has scaling equal to image width/height in user space.
                  // Transform unit square to get box in user space, then convert to screen.
                  const p0 = apply([0, 0], ctm);
                  const p1 = apply([1, 1], ctm);
                  const leftUS = Math.min(p0[0], p1[0]);
                  const rightUS = Math.max(p0[0], p1[0]);
                  const bottomUS = Math.min(p0[1], p1[1]);
                  const topUS = Math.max(p0[1], p1[1]);
                  // Convert to viewport (includes scaling) then to CSS top-left origin
                  const [leftPx, bottomPx] = apply(
                    [leftUS, bottomUS],
                    viewport.transform
                  );
                  const [rightPx, topPx] = apply(
                    [rightUS, topUS],
                    viewport.transform
                  );
                  const width = Math.abs(rightPx - leftPx);
                  const height = Math.abs(topPx - bottomPx);
                  // Convert Y to top-left
                  const topCss = viewport.height - Math.max(topPx, bottomPx);
                  imageRects.push({
                    left: Math.min(leftPx, rightPx),
                    top: topCss,
                    width,
                    height,
                  });
                  break;
                }
              }
            }
            if (imageRects.length === 0 && pageContainerRef.current) {
              // fallback to DOM <canvas> search (previous logic)
            }
            setImageBoxes(imageRects);
          }
        } catch (e) {
          console.warn("Image extraction via operator list failed", e);
        }

        // TEST: log the object for the "Carrier" label (e.g., "FORWARD AIR, INC")
        const forwardAirItem = findTextItem(textContent, "FORWARD AIR, INC");
        // eslint-disable-next-line no-console
        console.log("TextItem for 'FORWARD AIR' =>", forwardAirItem);
      } catch (err) {
        console.error("Failed to extract text boxes", err);
      }
    })();
  }, [pdfDoc, page]);

  // Build a proper file:// URL from the `file` query param.
  const decodedPath = decodeURIComponent(file);

  // Provide pdf.js with a fresh Uint8Array copy; avoids 'detached buffer'
  const fileSource = useMemo(() => {
    if (!pdfData) return undefined;
    return { data: new Uint8Array(pdfData) }; // copy
  }, [pdfData]);

  const combinedBoxes = useMemo(
    () => [...textBoxes, ...imageBoxes],
    [textBoxes, imageBoxes]
  );

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

        <label className="flex items-center gap-2 ml-4 text-sm">
          <input
            type="checkbox"
            checked={showObjects}
            onChange={(e) => setShowObjects(e.target.checked)}
          />
          Show objects
        </label>
      </div>

      <div className="w-full max-w-4xl overflow-y-auto border rounded-2xl bg-white p-4 relative">
        {fileSource && (
          <>
            <div
              ref={pageContainerRef}
              className="relative inline-block border-4"
            >
              <Document file={fileSource} onLoadSuccess={onLoadSuccess}>
                <Page
                  pageNumber={page}
                  renderTextLayer
                  renderAnnotationLayer
                  width={800}
                />
              </Document>
              {/* debug overlay – highlight text and image objects */}
              {showObjects && <PdfTextBoxOverlay boxes={combinedBoxes} />}
              {/* overlay for user selections */}
              <PdfFieldSelector
                key={page}
                initialBoxes={boxesPerPage[page] ?? []}
                onBoxesChange={handleBoxesChange}
              />
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
