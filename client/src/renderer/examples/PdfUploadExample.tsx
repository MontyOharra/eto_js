/**
 * Real-world example: Upload PDF to server
 * Demonstrates combining Electron APIs with HTTP requests
 */

import { useState } from 'react';
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

export function PdfUploadExample() {
  const [uploading, setUploading] = useState(false);
  const [uploadedFileId, setUploadedFileId] = useState<number | null>(null);

  const handleUploadPdf = async () => {
    setUploading(true);

    try {
      // Step 1: Use Electron to select file (OS native dialog)
      const selectedFile = await window.electron.selectFile({
        title: 'Select PDF to upload',
        filters: [{ name: 'PDF Files', extensions: ['pdf'] }],
      });

      if (!selectedFile) {
        setUploading(false);
        return;
      }

      // Step 2: Use Electron to read file content
      const fileData = await window.electron.readFile(selectedFile.filePath);

      // Step 3: Convert to base64 for HTTP upload
      const base64Content = btoa(fileData.content);

      // Step 4: Upload to FastAPI server via HTTP
      const response = await apiClient.post('/api/pdf-files', {
        file_name: selectedFile.fileName,
        content: base64Content,
        uploaded_by: 'current-user', // Would come from auth context
      });

      setUploadedFileId(response.data.id);

      console.log('PDF uploaded successfully!', response.data);
    } catch (error) {
      console.error('Upload failed:', error);

      // Show error dialog using Electron
      await window.electron.confirm(
        'Failed to upload PDF. Please try again.',
        {
          title: 'Upload Error',
        }
      );
    } finally {
      setUploading(false);
    }
  };

  const handleDeletePdf = async () => {
    if (!uploadedFileId) return;

    // Confirm deletion using Electron's native dialog
    const confirmed = await window.electron.confirm(
      'Delete this PDF from the server?',
      {
        title: 'Confirm Deletion',
        detail: 'This will permanently remove the file.',
      }
    );

    if (!confirmed) return;

    try {
      // Delete via HTTP API
      await apiClient.delete(`/api/pdf-files/${uploadedFileId}`);
      setUploadedFileId(null);
      console.log('PDF deleted successfully');
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">PDF Upload to Server</h2>

      <div className="space-y-4">
        <button
          onClick={handleUploadPdf}
          disabled={uploading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {uploading ? 'Uploading...' : 'Upload PDF'}
        </button>

        {uploadedFileId && (
          <div className="p-4 bg-green-100 rounded">
            <p className="text-green-800">
              ✓ PDF uploaded successfully! (ID: {uploadedFileId})
            </p>
            <button
              onClick={handleDeletePdf}
              className="mt-2 px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
            >
              Delete from Server
            </button>
          </div>
        )}
      </div>

      {/*
        Architecture summary:
        1. Electron IPC: Select file from OS
        2. Electron IPC: Read file content
        3. HTTP: Send to FastAPI server
        4. HTTP: All subsequent operations use server data

        The PDF is now stored on the server - the client just displays/manages it via HTTP
      */}
    </div>
  );
}
