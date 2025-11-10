import { TemplateListItem } from "../../types";
import { TemplateStatusBadge } from "./TemplateStatusBadge";

interface TemplateCardProps {
  template: TemplateListItem;
  onView?: (templateId: number) => void;
  onActivate?: (templateId: number) => void;
  onDeactivate?: (templateId: number) => void;
}

export function TemplateCard({
  template,
  onView,
  onActivate,
  onDeactivate,
}: TemplateCardProps) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 hover:border-gray-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="text-lg font-semibold text-white truncate">
              {template.name}
            </h3>
            <TemplateStatusBadge status={template.status} />
          </div>
          {/* Fixed height description area - always renders to keep layout consistent */}
          <div className="h-10">
            <p className="text-sm text-gray-400 line-clamp-2">
              {template.description || ""}
            </p>
          </div>
        </div>
      </div>

      {/* Template Info */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Current Version:</span>
          <span className="text-gray-200 font-medium">
            v{template.current_version.version_num}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Total Versions:</span>
          <span className="text-gray-200">{template.total_versions}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Usage Count:</span>
          <span className="text-gray-200">
            {template.current_version.usage_count} runs
          </span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 pt-3 border-t border-gray-700">
        {onView && (
          <button
            onClick={() => onView(template.id)}
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            View Details
          </button>
        )}
        {template.status === "inactive" && onActivate && (
          <button
            onClick={() => onActivate(template.id)}
            className="px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
          >
            Activate
          </button>
        )}
        {template.status === "active" && onDeactivate && (
          <button
            onClick={() => onDeactivate(template.id)}
            className="px-3 py-1.5 text-sm bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors"
          >
            Deactivate
          </button>
        )}
      </div>
    </div>
  );
}
