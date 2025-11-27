import { EtoSubRunStatus } from '../../types';

interface EtoPageHeaderProps {
  title: string;
  subtitle: string;
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  subRunStatusFilter: EtoSubRunStatus | 'all';
  onSubRunStatusFilterChange: (status: EtoSubRunStatus | 'all') => void;
  readFilter: 'all' | 'read' | 'unread';
  onReadFilterChange: (filter: 'all' | 'read' | 'unread') => void;
  onClearFilters: () => void;
}

export function EtoPageHeader({
  title,
  subtitle,
  searchQuery,
  onSearchQueryChange,
  subRunStatusFilter,
  onSubRunStatusFilterChange,
  readFilter,
  onReadFilterChange,
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
        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search filename, email, subject..."
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            className="w-72 px-4 py-2 pl-10 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
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

        {/* Sub-run Status Filter Dropdown */}
        <select
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={subRunStatusFilter}
          onChange={(e) => onSubRunStatusFilterChange(e.target.value as EtoSubRunStatus | 'all')}
        >
          <option value="all">All Runs</option>
          <option value="needs_template">Has Needs Template</option>
          <option value="failure">Has Failures</option>
          <option value="success">Has Success</option>
          <option value="processing">Has Processing</option>
          <option value="skipped">Has Skipped</option>
        </select>

        {/* Read/Unread Filter */}
        <select
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={readFilter}
          onChange={(e) => onReadFilterChange(e.target.value as 'all' | 'read' | 'unread')}
        >
          <option value="all">All</option>
          <option value="unread">Unread</option>
          <option value="read">Read</option>
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
