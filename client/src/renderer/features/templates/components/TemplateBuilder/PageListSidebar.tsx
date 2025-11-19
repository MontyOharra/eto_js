/**
 * PageListSidebar
 * Left sidebar showing scrollable list of all pages as rows
 * Allows quick selection/deselection and navigation
 */

interface PageListSidebarProps {
  totalPages: number;
  selectedPages: number[];
  onTogglePage: (pageIndex: number) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onFocusPage: (pageIndex: number) => void;
}

export function PageListSidebar({
  totalPages,
  selectedPages,
  onTogglePage,
  onSelectAll,
  onDeselectAll,
  onFocusPage,
}: PageListSidebarProps) {
  const selectedSet = new Set(selectedPages);

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-white font-semibold mb-3">
          Pages
        </h3>
        <div className="text-sm text-gray-400 mb-3">
          {selectedPages.length} of {totalPages} selected
        </div>
        <div className="flex gap-2">
          <button
            onClick={onSelectAll}
            className="flex-1 px-2 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            Select All
          </button>
          <button
            onClick={onDeselectAll}
            disabled={selectedPages.length === 0}
            className="flex-1 px-2 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Scrollable page list */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {Array.from({ length: totalPages }, (_, i) => {
            const pageIndex = i;
            const isSelected = selectedSet.has(pageIndex);

            return (
              <div
                key={pageIndex}
                className={`
                  flex items-center gap-2 p-2 rounded transition-colors
                  ${isSelected ? 'bg-blue-600/20 hover:bg-blue-600/30' : 'hover:bg-gray-800'}
                `}
              >
                {/* Selection checkbox */}
                <button
                  onClick={() => onTogglePage(pageIndex)}
                  className="flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors"
                  style={{
                    borderColor: isSelected ? '#3b82f6' : '#4b5563',
                    backgroundColor: isSelected ? '#3b82f6' : 'transparent',
                  }}
                >
                  {isSelected && (
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </button>

                {/* Page label - clickable to toggle */}
                <div
                  onClick={() => onTogglePage(pageIndex)}
                  className="flex-1 text-gray-300 text-sm cursor-pointer"
                >
                  Page {pageIndex + 1}
                </div>

                {/* Jump to page button */}
                <button
                  onClick={() => onFocusPage(pageIndex)}
                  className="flex-shrink-0 p-1 rounded hover:bg-gray-700 transition-colors"
                  title="Jump to page"
                >
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
