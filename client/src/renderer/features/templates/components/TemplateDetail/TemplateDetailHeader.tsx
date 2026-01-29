/**
 * TemplateDetailHeader
 * Header component with template name, version selector, and edit button
 */

import type { VersionListItem } from '../../types';

interface TemplateDetailHeaderProps {
  templateName: string;
  customerName: string | null;
  customerId: number | null;
  versions: VersionListItem[];
  selectedVersionId: number | null;
  currentVersionId: number | null;
  onVersionChange: (versionId: number) => void;
  /** Optional edit handler - if not provided, Edit button is hidden */
  onEdit?: () => void;
  /** Optional test match handler - if not provided, Test Match button is hidden */
  onTestMatch?: () => void;
}

export function TemplateDetailHeader({
  templateName,
  customerName,
  customerId,
  versions,
  selectedVersionId,
  currentVersionId,
  onVersionChange,
  onEdit,
  onTestMatch,
}: TemplateDetailHeaderProps) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <h2 className="text-xl font-semibold text-white">{templateName}</h2>
          {(customerName || customerId) && (
            <span className="text-sm text-gray-400">
              ({customerName || `Customer #${customerId}`})
            </span>
          )}
        </div>

        {/* Version selector */}
        {versions.length > 0 && (
          <div className="flex items-center space-x-2 border-l border-gray-600 pl-4">
            <label className="text-sm text-gray-400">Version:</label>
            <select
              value={selectedVersionId || ''}
              onChange={(e) => onVersionChange(Number(e.target.value))}
              className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-1.5 focus:ring-blue-500 focus:border-blue-500"
            >
              {versions.map((version) => (
                <option key={version.version_id} value={version.version_id}>
                  v{version.version_number}
                  {version.version_id === currentVersionId ? ' (current)' : ''}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Right side: Action buttons */}
      <div className="flex items-center space-x-2">
        {onTestMatch && (
          <button
            onClick={onTestMatch}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors font-medium flex items-center space-x-2"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
              />
            </svg>
            <span>Test Match</span>
          </button>
        )}
        {onEdit && (
          <button
            onClick={onEdit}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium flex items-center space-x-2"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
            <span>Edit</span>
          </button>
        )}
      </div>
    </div>
  );
}
