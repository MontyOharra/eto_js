/**
 * Folder Selection Step (Step 2)
 * Allows user to select a folder to monitor
 */

import type { EmailFolder } from '../../../types';

interface FolderSelectionStepProps {
  folders: EmailFolder[];
  selectedFolder: string | null;
  emailAccount: string;
  isLoading: boolean;
  onSelectFolder: (folder: EmailFolder) => void;
  onRetry: () => void;
}

export function FolderSelectionStep({
  folders,
  selectedFolder,
  emailAccount,
  isLoading,
  onSelectFolder,
  onRetry,
}: FolderSelectionStepProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
        <span className="ml-3 text-gray-400">Loading folders...</span>
      </div>
    );
  }

  if (folders.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400 mb-4">No folders found for this email account.</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-medium text-white mb-2">Select Folder</h3>
      <p className="text-gray-400 mb-4">
        Choose the folder to monitor from <strong className="text-white">{emailAccount}</strong>
      </p>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {folders.map((folder) => (
          <button
            key={folder.folder_name}
            onClick={() => onSelectFolder(folder)}
            className={`w-full text-left p-4 border-2 rounded-lg transition-colors ${
              selectedFolder === folder.folder_name
                ? 'border-blue-500 bg-blue-900/20'
                : 'border-gray-600 hover:border-gray-500 hover:bg-gray-700/50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-white">{folder.folder_name}</h4>
                <p className="text-sm text-gray-400">{folder.folder_path}</p>
              </div>
              {selectedFolder === folder.folder_name && (
                <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
