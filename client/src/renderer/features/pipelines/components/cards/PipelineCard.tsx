import { PipelineListItem } from '../../types';
import { formatTimestamp } from '../../../../shared/utils/formatUtils';

interface PipelineCardProps {
  pipeline: PipelineListItem;
  onView?: (pipelineId: number) => void;
}

export function PipelineCard({
  pipeline,
  onView,
}: PipelineCardProps) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 hover:border-gray-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-white">
            Pipeline #{pipeline.id}
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            Development/Testing Only
          </p>
        </div>
      </div>

      {/* Pipeline Info */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Compiled Plan:</span>
          <span className="text-gray-200 font-mono">
            {pipeline.compiled_plan_id !== null ? `#${pipeline.compiled_plan_id}` : 'Not compiled'}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Created:</span>
          <span className="text-gray-200 text-xs">
            {formatTimestamp(pipeline.created_at)}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Updated:</span>
          <span className="text-gray-200 text-xs">
            {formatTimestamp(pipeline.updated_at)}
          </span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 pt-3 border-t border-gray-700">
        {onView && (
          <button
            onClick={() => onView(pipeline.id)}
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            View Graph
          </button>
        )}
      </div>
    </div>
  );
}
