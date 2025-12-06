/**
 * PendingUpdatesHeader Component
 *
 * Header with title, search, and filters for the Pending Updates view.
 */

import type { PendingUpdateSortOption } from '../../types';

interface PendingUpdatesHeaderProps {
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  sortOption: PendingUpdateSortOption;
  onSortOptionChange: (option: PendingUpdateSortOption) => void;
  onClearFilters: () => void;
  /** Count of selected updates for bulk actions */
  selectedCount: number;
  onBulkApprove: () => void;
  onBulkReject: () => void;
}

export function PendingUpdatesHeader({
  searchQuery,
  onSearchQueryChange,
  sortOption,
  onSortOptionChange,
  onClearFilters,
  selectedCount,
  onBulkApprove,
  onBulkReject,
}: PendingUpdatesHeaderProps) {
  return (
    <div className="px-6 pt-6 pb-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 className="text-3xl font-bold text-white">Pending Updates</h1>
        <p className="text-gray-400 mt-2">
          Review and approve changes to existing orders
        </p>
      </div>

      {/* Search, Filter, and Bulk Actions Section */}
      <div className="flex items-center gap-3">
        {/* Bulk Actions (shown when items selected) */}
        {selectedCount > 0 && (
          <div className="flex items-center gap-2 mr-4 px-3 py-1 bg-gray-700 rounded-lg">
            <span className="text-sm text-gray-300">
              {selectedCount} selected
            </span>
            <button
              onClick={onBulkApprove}
              className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors"
            >
              Approve All
            </button>
            <button
              onClick={onBulkReject}
              className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
            >
              Reject All
            </button>
          </div>
        )}

        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search by HAWB or order #..."
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            className="w-64 px-4 py-2 pl-10 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <svg
            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        {/* Sort Dropdown */}
        <select
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={sortOption}
          onChange={(e) =>
            onSortOptionChange(e.target.value as PendingUpdateSortOption)
          }
        >
          <option value="proposed_at-desc">Proposed (Newest)</option>
          <option value="proposed_at-asc">Proposed (Oldest)</option>
          <option value="order_number-asc">Order # (Asc)</option>
          <option value="order_number-desc">Order # (Desc)</option>
        </select>

        {/* Clear Filters Button */}
        <button
          onClick={onClearFilters}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
