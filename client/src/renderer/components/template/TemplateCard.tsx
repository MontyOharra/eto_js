import { TemplateSummary, EtoDataTransforms } from "../../types/eto";

interface TemplateCardProps {
  template: TemplateSummary;
  onEdit: (template: TemplateSummary) => void;
  onView: (template: TemplateSummary) => void;
  onSetInactive: (template: TemplateSummary) => void;
}

export function TemplateCard({
  template,
  onEdit,
  onView,
  onSetInactive,
}: TemplateCardProps) {
  const getStatusColor = (status: TemplateSummary["status"]) => {
    switch (status) {
      case "active":
        return "bg-green-600";
      case "inactive":
        return "bg-orange-600";
      case "draft":
        return "bg-yellow-600";
      case "archived":
        return "bg-gray-600";
      default:
        return "bg-gray-600";
    }
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors">
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-blue-300 mb-1">
            {template.name}
          </h3>
          {template.customer_name && (
            <p className="text-sm text-gray-400">{template.customer_name}</p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <span
            className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(template.status)} text-white`}
          >
            {template.status}
          </span>
        </div>
      </div>

      {/* Description */}
      {template.description && (
        <p className="text-gray-300 text-sm mb-3 line-clamp-2">
          {template.description}
        </p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
        <div>
          <p className="text-gray-400">Usage</p>
          <p className="text-white font-medium">
            {template.usage_count.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-gray-400">Success Rate</p>
          <p className="text-white font-medium">
            {template.success_rate ? `${template.success_rate.toFixed(1)}%` : "N/A"}
          </p>
        </div>
        <div>
          <p className="text-gray-400">Rules</p>
          <p className="text-white font-medium">
            {template.extraction_rules_count || 0}
          </p>
        </div>
      </div>

      {/* Completeness Indicator */}
      <div className="flex items-center space-x-2 mb-4">
        <div className="flex items-center space-x-1">
          <div className={`w-2 h-2 rounded-full ${EtoDataTransforms.getTemplateCompletenessColor(template.is_complete)}`}></div>
          <span className="text-xs text-gray-400">
            {template.is_complete ? 'Complete' : 'Incomplete'}
          </span>
        </div>
        {template.last_used_at && (
          <span className="text-xs text-gray-500">
            Used {formatDate(template.last_used_at)}
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="flex justify-between items-center">
        <div className="text-xs text-gray-500">
          {template.updated_at ? `Updated ${formatDate(template.updated_at)}` : 'No update date'}
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => onView(template)}
            className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            View
          </button>
          {template.status !== 'inactive' && (
            <button
              onClick={() => onSetInactive(template)}
              className="px-3 py-1 text-xs bg-orange-600 hover:bg-orange-700 text-white rounded transition-colors"
            >
              Set Inactive
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
