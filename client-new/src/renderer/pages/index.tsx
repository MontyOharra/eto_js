import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';

export const Route = createFileRoute('/')({
  component: HomePage,
});

function HomePage() {
  const [output, setOutput] = useState<string>('');

  const handleSelectFile = async () => {
    try {
      const result = await window.electron.selectFile({
        properties: ['openFile'],
      });

      if (result.canceled) {
        setOutput('File selection canceled');
      } else {
        setOutput(`Selected files:\n${result.filePaths.join('\n')}`);
      }
    } catch (error) {
      setOutput(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleReadFile = async () => {
    try {
      // First select a file
      const selectResult = await window.electron.selectFile({
        properties: ['openFile'],
      });

      if (selectResult.canceled) {
        setOutput('File selection canceled');
        return;
      }

      // Then read the file
      const readResult = await window.electron.readFile({
        filePath: selectResult.filePaths[0],
      });

      if (readResult.error) {
        setOutput(`Error reading file: ${readResult.error}`);
      } else {
        setOutput(`File content (${selectResult.filePaths[0]}):\n\n${readResult.content.substring(0, 500)}${readResult.content.length > 500 ? '...' : ''}`);
      }
    } catch (error) {
      setOutput(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleSaveFile = async () => {
    try {
      const result = await window.electron.saveFile({
        defaultPath: 'test-output.txt',
        filters: [{ name: 'Text Files', extensions: ['txt'] }],
      });

      if (result.canceled) {
        setOutput('Save dialog canceled');
      } else {
        setOutput(`Save path selected: ${result.filePath}`);
      }
    } catch (error) {
      setOutput(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleConfirmDialog = async () => {
    try {
      const result = await window.electron.confirmDialog({
        title: 'Test Confirmation',
        message: 'This is a test confirmation dialog',
        detail: 'Click OK to confirm or Cancel to dismiss',
      });

      setOutput(`Dialog result: ${result.confirmed ? 'Confirmed (OK)' : 'Canceled'}\nResponse code: ${result.response}`);
    } catch (error) {
      setOutput(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="py-12 px-4">
      <h2 className="text-4xl font-bold text-gray-900 mb-4 text-center">
        Phase 4: File Operations Test
      </h2>
      <p className="text-xl text-gray-600 mb-8 text-center">
        Testing Electron IPC communication
      </p>

      <div className="max-w-2xl mx-auto space-y-6">
        {/* Test Buttons */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">File Operations</h3>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={handleSelectFile}
              className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded"
            >
              Select File
            </button>
            <button
              onClick={handleReadFile}
              className="bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-4 rounded"
            >
              Read File
            </button>
            <button
              onClick={handleSaveFile}
              className="bg-purple-500 hover:bg-purple-600 text-white font-semibold py-2 px-4 rounded"
            >
              Save Dialog
            </button>
            <button
              onClick={handleConfirmDialog}
              className="bg-orange-500 hover:bg-orange-600 text-white font-semibold py-2 px-4 rounded"
            >
              Confirm Dialog
            </button>
          </div>
        </div>

        {/* Output Display */}
        <div className="bg-gray-900 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 text-white">Output</h3>
          <pre className="text-green-400 font-mono text-sm whitespace-pre-wrap">
            {output || 'Click a button to test file operations...'}
          </pre>
        </div>

        {/* Info */}
        <div className="bg-blue-50 rounded-lg p-4 text-sm text-blue-800">
          <p className="font-semibold mb-2">Testing Phase 4 Implementation:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Type-safe IPC communication</li>
            <li>File selection dialogs</li>
            <li>File reading operations</li>
            <li>Save dialogs</li>
            <li>Confirmation dialogs</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
