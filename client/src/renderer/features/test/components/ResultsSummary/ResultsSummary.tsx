interface ResultsSummaryProps {
  startIndex: number;
  endIndex: number;
  totalCount: number;
  sortBy: string;
  onSortChange: (sortBy: string) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
  hasPrevPage: boolean;
  hasNextPage: boolean;
  activeFilters?: React.ReactNode;
}

export function ResultsSummary({
  startIndex,
  endIndex,
  totalCount,
  sortBy,
  onSortChange,
  onPrevPage,
  onNextPage,
  hasPrevPage,
  hasNextPage,
  activeFilters,
}: ResultsSummaryProps) {
  return (
    <div className="px-6 pb-4 flex items-center justify-between flex-shrink-0">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4">
          <span className="text-gray-400 text-sm">
            <span className="text-white font-semibold">{startIndex}-{endIndex}</span> of <span className="text-white font-semibold">{totalCount}</span>
          </span>

          {/* Pagination Controls (Gmail style) */}
          <div className="flex items-center gap-1">
            <button
              onClick={onPrevPage}
              className="p-1.5 hover:bg-gray-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={!hasPrevPage}
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              onClick={onNextPage}
              className="p-1.5 hover:bg-gray-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={!hasNextPage}
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Active Filters Pills */}
        {activeFilters && (
          <div className="flex items-center gap-2">
            {activeFilters}
          </div>
        )}
      </div>

      {/* Sort Dropdown */}
      <select
        className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        value={sortBy}
        onChange={(e) => onSortChange(e.target.value)}
      >
        <option value="updated_desc">Last Updated (Newest)</option>
        <option value="updated_asc">Last Updated (Oldest)</option>
        <option value="created_desc">Created (Newest)</option>
        <option value="created_asc">Created (Oldest)</option>
        <option value="filename_asc">Filename (A-Z)</option>
        <option value="filename_desc">Filename (Z-A)</option>
        <option value="status_asc">Status</option>
      </select>
    </div>
  );
}
