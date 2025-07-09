import { useState, type ChangeEvent } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

export default function Temp() {
  const [file, setFile] = useState<File | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);

  // Handle file selection
  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
    } else {
      alert("Please select a PDF file.");
    }
    console.log(selected);
  };

  // Callback once PDF metadata is loaded
  const onLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  return (
    <main className="min-h-screen bg-gray-100 flex flex-col items-center p-8">
      {/* Hidden file input controlled by a styled label/button */}
      <label
        htmlFor="pdfInput"
        className="cursor-pointer px-6 py-3 bg-indigo-600 text-white rounded-2xl shadow-lg hover:bg-indigo-700 mb-4 transition"
      >
        Select PDF to view
      </label>
      <input
        id="pdfInput"
        type="file"
        accept="application/pdf"
        onChange={onFileChange}
        className="hidden"
      />

      {/* Render PDF once a file is selected */}
      {file && (
        <div className="w-full max-w-4xl overflow-y-auto border rounded-2xl shadow-inner bg-white p-4">
          <Document file={file} onLoadSuccess={onLoadSuccess}>
            {Array.from(new Array(numPages), (el, index) => (
              <Page
                key={`page_${index + 1}`}
                pageNumber={index + 1}
                renderTextLayer
                renderAnnotationLayer
                width={800}
              />
            ))}
          </Document>
        </div>
      )}
    </main>
  );
}
