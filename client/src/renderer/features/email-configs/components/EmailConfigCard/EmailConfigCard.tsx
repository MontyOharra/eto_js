/**
 * Email Config Card Component
 * Displays individual email ingestion configuration with actions
 */

import type { IngestionConfigListItem } from "../../types";
import { StatusBadge } from "./StatusBadge";
import { formatUtcToLocal } from "../../../../shared/utils/dateUtils";

interface EmailConfigCardProps {
  config: IngestionConfigListItem;
  onEdit?: (id: number) => void;
  onDelete?: (id: number) => void;
  onActivate?: (id: number) => void;
  onDeactivate?: (id: number) => void;
  isActivating?: boolean;
  isDeactivating?: boolean;
}

export function EmailConfigCard({
  config,
  onEdit,
  onDelete,
  onActivate,
  onDeactivate,
  isActivating = false,
  isDeactivating = false,
}: EmailConfigCardProps) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 hover:border-gray-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="text-lg font-semibold text-white truncate">
              {config.name}
            </h3>
            <div className="flex items-center space-x-2">
              {config.is_active && <StatusBadge type="active" />}
              {!config.is_active && <StatusBadge type="inactive" />}
              {config.last_error_message && <StatusBadge type="error" />}
            </div>
          </div>
          {config.description && (
            <p className="text-sm text-gray-400 line-clamp-2">
              {config.description}
            </p>
          )}
        </div>
      </div>

      {/* Configuration Info */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Email Account:</span>
          <span className="text-gray-200 font-medium truncate ml-2 max-w-[60%]" title={config.account_email}>
            {config.account_email}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Folder:</span>
          <span className="text-gray-200">{config.folder_name}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Last Check:</span>
          <span className="text-gray-200">
            {formatUtcToLocal(config.last_check_time)}
          </span>
        </div>
      </div>

      {/* Error Message */}
      {config.last_error_message && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-700 rounded">
          <div className="flex items-start space-x-2">
            <svg
              className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-red-300 line-clamp-2">
                {config.last_error_message}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 pt-3 border-t border-gray-700">
        {/* Activate button - shown when inactive */}
        {!config.is_active && onActivate && (
          <button
            onClick={() => onActivate(config.id)}
            disabled={isActivating}
            className="px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            {isActivating ? "Activating..." : "Activate"}
          </button>
        )}

        {/* Deactivate button - shown when active */}
        {config.is_active && onDeactivate && (
          <button
            onClick={() => onDeactivate(config.id)}
            disabled={isDeactivating}
            className="px-3 py-1.5 text-sm bg-yellow-600 hover:bg-yellow-700 disabled:bg-yellow-800 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            {isDeactivating ? "Deactivating..." : "Deactivate"}
          </button>
        )}

        {onEdit && (
          <button
            onClick={() => onEdit(config.id)}
            disabled={config.is_active}
            className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
            title={
              config.is_active ? "Deactivate to edit" : "Edit configuration"
            }
          >
            Edit
          </button>
        )}

        {!config.is_active && onDelete && (
          <button
            onClick={() => onDelete(config.id)}
            className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}
