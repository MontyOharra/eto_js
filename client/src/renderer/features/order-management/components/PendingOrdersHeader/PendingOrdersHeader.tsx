/**
 * PendingOrdersHeader Component
 *
 * Header with title, search, and filters for the Pending Orders view.
 */

import type { PendingOrderStatus, PendingOrderSortOption } from '../../types';

interface PendingOrdersHeaderProps {
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  statusFilter: PendingOrderStatus | 'all';
  onStatusFilterChange: (status: PendingOrderStatus | 'all') => void;
  sortOption: PendingOrderSortOption;
  onSortOptionChange: (option: PendingOrderSortOption) => void;
  onClearFilters: () => void;
}

export function PendingOrdersHeader({
  searchQuery,
  onSearchQueryChange,
  statusFilter,
  onStatusFilterChange,
  sortOption,
  onSortOptionChange,
  onClearFilters,
}: PendingOrdersHeaderProps) {
  return (
    <div className="px-6 pt-6 pb-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 className="text-3xl font-bold text-white">Pending Orders</h1>
        <p className="text-gray-400 mt-2">
          Orders being compiled from multiple ETO runs
        </p>
      </div>

      {/* Search and Filter Section */}
      <div className="flex items-center gap-3">
        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search by HAWB..."
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

        {/* Status Filter Dropdown */}
        <select
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={statusFilter}
          onChange={(e) =>
            onStatusFilterChange(e.target.value as PendingOrderStatus | 'all')
          }
        >
          <option value="all">All Status</option>
          <option value="incomplete">Incomplete</option>
          <option value="ready">Ready to Create</option>
          <option value="created">Created</option>
        </select>

        {/* Sort Dropdown */}
        <select
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={sortOption}
          onChange={(e) =>
            onSortOptionChange(e.target.value as PendingOrderSortOption)
          }
        >
          <option value="updated_at-desc">Last Updated (Newest)</option>
          <option value="updated_at-asc">Last Updated (Oldest)</option>
          <option value="created_at-desc">Created (Newest)</option>
          <option value="created_at-asc">Created (Oldest)</option>
          <option value="hawb-asc">HAWB (A-Z)</option>
          <option value="hawb-desc">HAWB (Z-A)</option>
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
