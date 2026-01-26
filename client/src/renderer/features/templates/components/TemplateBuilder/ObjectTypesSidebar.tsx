/**
 * ObjectTypesSidebar
 * Left sidebar with template metadata inputs and object type visibility toggles
 */

import { ObjectTypeAccordion } from './ObjectTypeAccordion';
import { CustomerSelect } from './CustomerSelect';
import { OBJECT_TYPE_NAMES, OBJECT_TYPE_COLORS } from '../../constants';

interface ObjectItem {
  id: string;
  page: number;
  text?: string;
  bbox: [number, number, number, number];
  type: string;
  [key: string]: any;
}

interface ObjectTypesSidebarProps {
  templateName: string;
  templateDescription: string;
  customerId: number | null;
  disableCustomerChange?: boolean;
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onCustomerIdChange: (customerId: number | null) => void;
  typeCounts: Record<string, number>;
  selectedTypeCounts: Record<string, number>;
  objectsByType: Record<string, ObjectItem[]>;
  selectedObjectIds: Set<string>;
  visibleTypes: Set<string>;
  onObjectToggle: (objectId: string) => void;
  onTypeToggle: (type: string) => void;
  onShowAll: () => void;
  onHideAll: () => void;
  onCopyFromExisting?: () => void;
}

export function ObjectTypesSidebar({
  templateName,
  templateDescription,
  customerId,
  disableCustomerChange = false,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  onCustomerIdChange,
  typeCounts,
  selectedTypeCounts,
  objectsByType,
  selectedObjectIds,
  visibleTypes,
  onObjectToggle,
  onTypeToggle,
  onShowAll,
  onHideAll,
  onCopyFromExisting,
}: ObjectTypesSidebarProps) {
  // Calculate total selected objects
  const totalSelected = Object.values(selectedTypeCounts).reduce((sum, count) => sum + count, 0);
  return (
    <div className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
      {/* Template Name & Description */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-white mb-3">Template Information</h3>
        <div className="space-y-3">
          <div>
            <label htmlFor="template-name" className="block text-xs font-medium text-gray-300 mb-1.5">
              Template Name *
            </label>
            <input
              id="template-name"
              type="text"
              value={templateName}
              onChange={(e) => onTemplateNameChange(e.target.value)}
              placeholder="Enter template name..."
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <CustomerSelect
            value={customerId}
            onChange={onCustomerIdChange}
            disabled={disableCustomerChange}
          />
          <div>
            <label htmlFor="template-description" className="block text-xs font-medium text-gray-300 mb-1.5">
              Description
            </label>
            <textarea
              id="template-description"
              value={templateDescription}
              onChange={(e) => onTemplateDescriptionChange(e.target.value)}
              placeholder="Enter description (optional)..."
              rows={3}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
            />
          </div>
        </div>
      </div>

      {/* Copy from Existing Template */}
      {onCopyFromExisting && (
        <div className="mb-6">
          <button
            onClick={onCopyFromExisting}
            className="w-full px-3 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors font-medium"
          >
            Copy from Existing Template
          </button>
        </div>
      )}

      {/* Object Visibility Section */}
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

      {/* Object Type Accordions */}
      <div className="space-y-2">
        {Object.entries(OBJECT_TYPE_NAMES).map(([type, label]) => {
          const count = typeCounts[type] || 0;
          const selectedCount = selectedTypeCounts[type] || 0;
          const objects = objectsByType[type] || [];
          const isVisible = visibleTypes.has(type);

          // Don't render if no objects of this type
          if (count === 0) return null;

          return (
            <ObjectTypeAccordion
              key={type}
              label={label}
              color={OBJECT_TYPE_COLORS[type]}
              count={count}
              selectedCount={selectedCount}
              objects={objects}
              selectedObjectIds={selectedObjectIds}
              isVisible={isVisible}
              onObjectToggle={onObjectToggle}
              onVisibilityToggle={() => onTypeToggle(type)}
            />
          );
        })}
      </div>

      {/* Total Selection Indicator */}
      {totalSelected > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-300 font-medium">Selected:</span>
            <span className="text-blue-400 font-semibold">{totalSelected} objects</span>
          </div>
        </div>
      )}
    </div>
  );
}
