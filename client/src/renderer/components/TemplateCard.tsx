import { Template } from "../data/mockTemplates";

interface TemplateCardProps {
  template: Template;
  onEdit: (template: Template) => void;
  onView: (template: Template) => void;
  onDelete: (template: Template) => void;
}

export function TemplateCard({
  template,
  onEdit,
  onView,
  onDelete,
}: TemplateCardProps) {
  const getStatusColor = (status: Template["status"]) => {
    switch (status) {
      case "active":
        return "bg-green-600";
      case "draft":
        return "bg-yellow-600";
      case "testing":
        return "bg-blue-600";
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
          {template.customerName && (
            <p className="text-sm text-gray-400">{template.customerName}</p>
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
            {template.usageCount.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-gray-400">Success Rate</p>
          <p className="text-white font-medium">
            {template.successRate ? `${template.successRate}%` : "N/A"}
          </p>
        </div>
        <div>
          <p className="text-gray-400">Last Used</p>
          <p className="text-white font-medium">
            {template.lastUsedAt ? formatDate(template.lastUsedAt) : "Never"}
          </p>
        </div>
      </div>

      {/* Tags */}
      {template.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {template.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-1 text-xs bg-gray-700 text-gray-300 rounded"
            >
              {tag}
            </span>
          ))}
          {template.tags.length > 3 && (
            <span className="px-2 py-1 text-xs bg-gray-700 text-gray-300 rounded">
              +{template.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex justify-between items-center">
        <div className="text-xs text-gray-500">
          Updated {formatDate(template.updatedAt)}
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => onView(template)}
            className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            View
          </button>
          <button
            onClick={() => onEdit(template)}
            className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
          >
            Edit
          </button>
          <button
            onClick={() => onDelete(template)}
            className="px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
