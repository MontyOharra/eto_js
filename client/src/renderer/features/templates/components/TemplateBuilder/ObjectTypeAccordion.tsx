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
  isVisible: boolean;
  onObjectToggle: (objectId: string) => void;
  onVisibilityToggle: () => void;
}

export function ObjectTypeAccordion({
  label,
  color,
  count,
  selectedCount,
  objects,
  selectedObjectIds,
  isVisible,
  onObjectToggle,
  onVisibilityToggle,
}: ObjectTypeAccordionProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-gray-700 rounded overflow-hidden">
      {/* Header */}
      <div className="w-full flex items-center justify-between p-2.5 text-xs bg-gray-800">
        <div className="flex items-center space-x-2">
          {/* Expand/Collapse Button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-0.5 hover:bg-gray-700 rounded transition-colors"
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
          >
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
          </button>

          {/* Visibility Toggle Button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onVisibilityToggle();
            }}
            className="p-0.5 hover:bg-gray-700 rounded transition-colors"
            aria-label={isVisible ? 'Hide objects' : 'Show objects'}
          >
            {isVisible ? (
              <svg
                className="w-3.5 h-3.5 text-blue-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            ) : (
              <svg
                className="w-3.5 h-3.5 text-gray-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                />
              </svg>
            )}
          </button>

          {/* Color & Label */}
          <div
            className="w-3 h-3 rounded flex-shrink-0"
            style={{ backgroundColor: color }}
          />
          <span className="text-left text-white">{label}</span>
        </div>

        {/* Count Badge */}
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
      </div>

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
