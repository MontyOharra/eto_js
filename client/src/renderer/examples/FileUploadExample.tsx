/**
 * Example component demonstrating type-safe Electron API usage
 * Shows how to use file operations with full TypeScript safety
 */

import { useState } from 'react';

export function FileUploadExample() {
  const [fileContent, setFileContent] = useState<string>('');
  const [fileName, setFileName] = useState<string>('');

  const handleSelectAndReadFile = async () => {
    try {
      // Step 1: Open file dialog (type-safe!)
      const selectedFile = await window.electron.selectFile({
        title: 'Select a PDF file',
        filters: [
          { name: 'PDF Files', extensions: ['pdf'] },
          { name: 'All Files', extensions: ['*'] },
        ],
      });

      if (!selectedFile) {
        console.log('User canceled file selection');
        return;
      }

      setFileName(selectedFile.fileName);

      // Step 2: Read file content (type-safe!)
      const fileData = await window.electron.readFile(selectedFile.filePath);
      setFileContent(fileData.content);

      console.log('File loaded:', fileData.filePath);
    } catch (error) {
      console.error('Error loading file:', error);
    }
  };

  const handleSaveFile = async () => {
    try {
      const result = await window.electron.saveFile(fileContent, {
        defaultPath: fileName,
        filters: [{ name: 'Text Files', extensions: ['txt'] }],
      });

      if (result.success) {
        console.log('File saved to:', result.filePath);
      }
    } catch (error) {
      console.error('Error saving file:', error);
    }
  };

  const handleDeleteWithConfirmation = async () => {
    // Use Electron's native confirm dialog (type-safe!)
    const confirmed = await window.electron.confirm(
      'Are you sure you want to delete this file?',
      {
        title: 'Confirm Deletion',
        detail: 'This action cannot be undone.',
      }
    );

    if (confirmed) {
      // Perform deletion
      console.log('User confirmed deletion');
    } else {
      console.log('User canceled deletion');
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">File Operations Example</h2>

      <div className="space-y-4">
        <button
          onClick={handleSelectAndReadFile}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Select & Read File
        </button>

        {fileName && (
          <div className="p-4 bg-gray-100 rounded">
            <p className="font-semibold">File: {fileName}</p>
            <p className="text-sm text-gray-600 mt-2">
              Content length: {fileContent.length} characters
            </p>
          </div>
        )}

        <button
          onClick={handleSaveFile}
          disabled={!fileContent}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
        >
          Save File
        </button>

        <button
          onClick={handleDeleteWithConfirmation}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
          Delete with Confirmation
        </button>
      </div>

      {/* Notice: Full TypeScript autocomplete and type checking! */}
      {/*
        window.electron.selectFile() - TypeScript knows the return type
        window.electron.readFile() - TypeScript knows it needs a string
        window.electron.confirm() - TypeScript knows it returns a boolean
      */}
    </div>
  );
}
