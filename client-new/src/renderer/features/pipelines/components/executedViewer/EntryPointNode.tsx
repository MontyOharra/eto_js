/**
 * EntryPointNode
 * Read-only entry point node for executed pipeline viewer
 */

import { Handle, Position } from '@xyflow/react';

export interface EntryPointNodeProps {
  data: {
    label: string;
    fieldReference: string;
  };
}

export function EntryPointNode({ data }: EntryPointNodeProps) {
  return (
    <div className="bg-green-700 border-2 border-green-500 rounded-lg px-4 py-3 min-w-[180px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <svg className="w-4 h-4 text-green-300 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clipRule="evenodd" />
          </svg>
          <span className="text-sm font-semibold text-white">Entry Point</span>
        </div>
      </div>

      {/* Field Label */}
      <div className="text-center">
        <div className="text-xs text-green-200 mb-1">Field:</div>
        <div className="text-sm font-mono font-bold text-white">{data.label}</div>
      </div>

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id={data.fieldReference}
        className="!bg-green-400 !w-3 !h-3 !border-2 !border-green-200"
      />
    </div>
  );
}
