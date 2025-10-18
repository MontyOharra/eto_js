import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { EntryPoint } from '../../../../../../types/pipelineTypes';

interface EntryPointNodeProps {
  data: {
    entryPoint: EntryPoint;
    onHandleClick?: (nodeId: string, handleId: string, handleType: 'source' | 'target') => void;
  };
  id: string;
}

const TYPE_COLORS: Record<string, string> = {
  str: "#3B82F6", // blue-500
};

export const EntryPointNode = memo(({ data, id }: EntryPointNodeProps) => {
  const { entryPoint, onHandleClick } = data;
  const handleColor = TYPE_COLORS[entryPoint.type] || "#3B82F6";

  return (
    <div className="bg-gray-800 border-2 border-blue-500 rounded-lg shadow-lg min-w-[200px]">
      {/* Header */}
      <div className="bg-blue-600 px-3 py-2 rounded-t-md">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Entry Point</h3>
        </div>
      </div>

      {/* Body */}
      <div className="px-3 py-3">
        {/* Output Handle */}
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-300 font-medium">{entryPoint.name}</span>
          <Handle
            type="source"
            position={Position.Right}
            id={entryPoint.node_id}
            data-handleid={entryPoint.node_id}
            onClick={() => onHandleClick?.(id, entryPoint.node_id, 'source')}
            style={{
              position: 'relative',
              transform: 'none',
              top: 'auto',
              right: 'auto',
              width: '12px',
              height: '12px',
              backgroundColor: handleColor,
              border: '2px solid #1F2937',
              cursor: 'pointer',
            }}
          />
        </div>
        <div className="text-[10px] text-gray-500">Type: {entryPoint.type}</div>
      </div>
    </div>
  );
});

EntryPointNode.displayName = 'EntryPointNode';
