interface EtoPageHeaderProps {
  title: string;
  subtitle: string;
  searchScope: string;
  onSearchScopeChange: (scope: string) => void;
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  readFilter: string;
  onReadFilterChange: (filter: string) => void;
  onDateRangeClick: () => void;
  onClearFilters: () => void;
}

export function EtoPageHeader({
  title,
  subtitle,
  searchScope,
  onSearchScopeChange,
  searchQuery,
  onSearchQueryChange,
  statusFilter,
  onStatusFilterChange,
  readFilter,
  onReadFilterChange,
  onDateRangeClick,
  onClearFilters,
}: EtoPageHeaderProps) {
  return (
    <div className="px-6 pt-6 pb-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 className="text-3xl font-bold text-white">{title}</h1>
        <p className="text-gray-400 mt-2">{subtitle}</p>
      </div>

      {/* Search and Filter Section */}
      <div className="flex items-center gap-3">
        {/* Combined Search Input with Scope Selector */}
        <div className="flex items-center bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
          {/* Search Scope Dropdown */}
          <select
            className="px-3 py-2 bg-gray-750 text-white text-sm border-r border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={searchScope}
            onChange={(e) => onSearchScopeChange(e.target.value)}
          >
            <option value="filename">PDF Name</option>
            <option value="email">Email</option>
            <option value="all">All Fields</option>
          </select>

          {/* Search Input */}
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
              className="w-64 px-4 py-2 pl-10 bg-gray-800 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <svg
              className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Status Filter Dropdown */}
        <select
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value)}
        >
          <option value="all">All Status</option>
          <option value="success">Success</option>
          <option value="processing">Processing</option>
          <option value="failure">Failure</option>
          <option value="needs_template">Needs Template</option>
          <option value="not_started">Not Started</option>
          <option value="skipped">Skipped</option>
        </select>

        {/* Read/Unread Filter */}
        <select
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={readFilter}
          onChange={(e) => onReadFilterChange(e.target.value)}
        >
          <option value="all">All</option>
          <option value="unread">Unread</option>
          <option value="read">Read</option>
        </select>

        {/* Date Range Filter */}
        <button
          onClick={onDateRangeClick}
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white hover:bg-gray-700 transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span>Date Range</span>
        </button>

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
