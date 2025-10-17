/**
 * ObjectTypesSidebar
 * Left sidebar with object type visibility toggles
 */

import { ObjectTypeButton } from './ObjectTypeButton';

// Object type configurations
const OBJECT_TYPE_NAMES: Record<string, string> = {
  text_word: 'Text Words',
  text_line: 'Text Lines',
  graphic_rect: 'Rectangles',
  graphic_line: 'Lines',
  graphic_curve: 'Curves',
  image: 'Images',
  table: 'Tables',
};

const OBJECT_TYPE_COLORS: Record<string, string> = {
  text_word: '#ff0000',
  text_line: '#00ff00',
  graphic_rect: '#0000ff',
  graphic_line: '#ffff00',
  graphic_curve: '#ff00ff',
  image: '#00ffff',
  table: '#ffa500',
};

interface ObjectTypesSidebarProps {
  typeCounts: Record<string, number>;
  selectedTypes: Set<string>;
  onTypeToggle: (type: string) => void;
  onShowAll: () => void;
  onHideAll: () => void;
}

export function ObjectTypesSidebar({
  typeCounts,
  selectedTypes,
  onTypeToggle,
  onShowAll,
  onHideAll,
}: ObjectTypesSidebarProps) {
  return (
    <div className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
      <h3 className="text-sm font-semibold text-white mb-3">Object Visibility</h3>

      {/* Show/Hide All Buttons */}
      <div className="space-y-2 mb-4">
        <button
          onClick={onShowAll}
          className="w-full px-3 py-2 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors font-medium"
        >
          Show All Types
        </button>
        <button
          onClick={onHideAll}
          className="w-full px-3 py-2 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors font-medium"
        >
          Hide All Types
        </button>
      </div>

      {/* Object Type Buttons */}
      <div className="space-y-2">
        {Object.entries(OBJECT_TYPE_NAMES).map(([type, label]) => {
          const count = typeCounts[type] || 0;

          // Don't render if no objects of this type
          if (count === 0) return null;

          return (
            <ObjectTypeButton
              key={type}
              type={type}
              label={label}
              color={OBJECT_TYPE_COLORS[type]}
              count={count}
              isSelected={selectedTypes.has(type)}
              onToggle={() => onTypeToggle(type)}
            />
          );
        })}
      </div>
    </div>
  );
}
