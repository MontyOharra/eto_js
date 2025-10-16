import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/pdf-files')({
  component: PdfFilesPage,
});

function PdfFilesPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-4">PDF Files</h1>
      <p className="text-gray-600">
        Browse, upload, and view PDF files for order processing.
      </p>
      {/* TODO: Implement PDF viewer and file list */}
    </div>
  );
}
