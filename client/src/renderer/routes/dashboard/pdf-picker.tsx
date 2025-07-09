import { createFileRoute } from "@tanstack/react-router";
import { useState, type ChangeEvent } from "react";

// @ts-expect-error new route path pending in generated types
export const Route = createFileRoute("/dashboard/pdf-picker")({
  component: PdfPicker,
});

function PdfPicker() {
  const [file, setFile] = useState<File | null>(null);

  // Handle file selection
  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
    } else {
      alert("Please select a PDF file.");
    }
  };

  const onViewClick = async () => {
    if (!file) return;
    try {
      const filePath = window.electron.getFilePath(file);
      if (!filePath) {
        alert(
          "Unable to determine file path (Electron 32+ no longer exposes File.path)."
        );
        return;
      }
      await window.electron.openPdfWindow(filePath);
    } catch (err) {
      console.error(err);
      alert("Failed to open PDF viewer window.");
    }
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

      <button
        onClick={onViewClick}
        disabled={!file}
        className="px-6 py-3 bg-green-600 text-white rounded-2xl shadow-lg hover:bg-green-700 disabled:bg-gray-400 transition"
      >
        View
      </button>
    </main>
  );
}
