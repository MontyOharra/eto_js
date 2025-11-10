/**
 * ObjectTypeAccordion
 * Collapsible accordion for a PDF object type showing list of all objects
 * Allows individual object selection from sidebar
 */

import { useState } from 'react';

interface ObjectItem {
  id: string;
  page: number;
  text?: string;
  bbox: [number, number, number, number];
  [key: string]: any;
}

interface ObjectTypeAccordionProps {
  label: string;
  color: string;
  count: number;
  selectedCount: number;
  objects: ObjectItem[];
  selectedObjectIds: Set<string>;
  onObjectToggle: (objectId: string) => void;
}

export function ObjectTypeAccordion({
  label,
  color,
  count,
  selectedCount,
  objects,
  selectedObjectIds,
  onObjectToggle,
}: ObjectTypeAccordionProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-gray-700 rounded overflow-hidden">
      {/* Header Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-2.5 text-xs bg-gray-800 hover:bg-gray-700 transition-colors"
      >
        <div className="flex items-center space-x-2.5">
          <svg
            className={`w-3 h-3 text-gray-400 transition-transform ${
              isExpanded ? 'rotate-90' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
          <div
            className="w-3 h-3 rounded flex-shrink-0"
            style={{ backgroundColor: color }}
          />
          <span className="text-left text-white">{label}</span>
        </div>
        <div className="flex items-center space-x-2">
          {selectedCount > 0 && (
            <span className="text-blue-400 font-semibold">
              [{selectedCount}/{count}]
            </span>
          )}
          {selectedCount === 0 && (
            <span className="font-medium text-gray-500">({count})</span>
          )}
        </div>
      </button>

      {/* Object List */}
      {isExpanded && (
        <div className="max-h-64 overflow-y-auto bg-gray-850">
          {objects.map((obj) => {
            const isSelected = selectedObjectIds.has(obj.id);
            return (
              <button
                key={obj.id}
                onClick={() => onObjectToggle(obj.id)}
                className={`w-full text-left px-4 py-2 text-xs border-t border-gray-700 hover:bg-gray-700 transition-colors ${
                  isSelected ? 'bg-blue-900/30 text-blue-300' : 'text-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    {/* Text preview for text objects */}
                    {obj.text && (
                      <div className="font-medium truncate">
                        "{obj.text}"
                      </div>
                    )}
                    {/* Type description for non-text objects */}
                    {!obj.text && (
                      <div className="font-medium">
                        {label.slice(0, -1)} {/* Remove trailing 's' */}
                      </div>
                    )}
                    <div className="text-gray-500 text-[10px] mt-0.5">
                      Page {obj.page} • [{obj.bbox[0].toFixed(0)}, {obj.bbox[1].toFixed(0)}]
                    </div>
                  </div>
                  {isSelected && (
                    <svg
                      className="w-4 h-4 text-blue-400 flex-shrink-0 ml-2"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
