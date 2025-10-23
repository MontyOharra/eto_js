/**
 * ExecutedModuleNode
 * Read-only module node with execution data overlay
 */

import { useState } from 'react';
import { Handle, Position } from '@xyflow/react';

interface NodePin {
  node_id: string;
  name: string;
  type: string[];
}

export interface ExecutedModuleNodeProps {
  data: {
    moduleId: string;
    instanceId: string;
    inputs: NodePin[];
    outputs: NodePin[];
    config: Record<string, any>;
    // Execution data
    executed: boolean;
    executionInputs: Record<string, { value: any; type: string }> | null;
    executionOutputs: Record<string, { value: any; type: string }> | null;
    executionError: Record<string, any> | null;
  };
}

export function ExecutedModuleNode({ data }: ExecutedModuleNodeProps) {
  const {
    moduleId,
    instanceId,
    inputs,
    outputs,
    executed,
    executionInputs,
    executionOutputs,
    executionError,
  } = data;

  const [hoveredPin, setHoveredPin] = useState<string | null>(null);

  // Extract module name from module_id (e.g., "string_uppercase:1.0.0" -> "String Uppercase")
  const moduleName = moduleId.split(':')[0]
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  // Determine module color based on execution state
  const getBorderColor = () => {
    if (executionError) return 'border-red-500';
    if (executed) return 'border-blue-500';
    return 'border-gray-600';
  };

  const getBackgroundColor = () => {
    if (executionError) return 'bg-red-900/30';
    if (executed) return 'bg-gray-800';
    return 'bg-gray-800/50';
  };

  // Format execution value for display
  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'string') return `"${value}"`;
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  return (
    <div className={`${getBackgroundColor()} border-2 ${getBorderColor()} rounded-lg min-w-[300px] max-w-[400px]`}>
      {/* Header */}
      <div className="bg-gray-700 px-4 py-2 rounded-t-md border-b border-gray-600">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-white">{moduleName}</div>
            <div className="text-xs text-gray-400 font-mono">{instanceId}</div>
          </div>

          {/* Execution Status Badge */}
          {executionError ? (
            <div className="flex items-center text-xs text-red-300 bg-red-900/50 px-2 py-1 rounded">
              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              Failed
            </div>
          ) : executed ? (
            <div className="flex items-center text-xs text-green-300 bg-green-900/50 px-2 py-1 rounded">
              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Executed
            </div>
          ) : (
            <div className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">
              Not Executed
            </div>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Inputs */}
        {inputs.length > 0 && (
          <div>
            <div className="text-xs text-gray-400 mb-2 font-semibold">INPUTS</div>
            <div className="space-y-2">
              {inputs.map(input => {
                const executionValue = executionInputs?.[input.name];
                const pinId = `${instanceId}-input-${input.name}`;

                return (
                  <div
                    key={input.node_id}
                    className="relative flex items-center"
                    onMouseEnter={() => setHoveredPin(pinId)}
                    onMouseLeave={() => setHoveredPin(null)}
                  >
                    {/* Input Handle */}
                    <Handle
                      type="target"
                      position={Position.Left}
                      id={input.node_id}
                      className="!bg-blue-400 !w-3 !h-3 !border-2 !border-blue-200 !-left-1.5"
                    />

                    {/* Pin Info */}
                    <div className="flex-1 bg-gray-700 rounded px-3 py-2 ml-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-white">{input.name}</span>
                        <span className="text-xs text-gray-400 font-mono">{input.type[0]}</span>
                      </div>

                      {/* Execution Value */}
                      {executionValue && (
                        <div className="mt-1 text-xs text-blue-300 font-mono truncate" title={formatValue(executionValue.value)}>
                          {formatValue(executionValue.value)}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Outputs */}
        {outputs.length > 0 && (
          <div>
            <div className="text-xs text-gray-400 mb-2 font-semibold">OUTPUTS</div>
            <div className="space-y-2">
              {outputs.map(output => {
                const executionValue = executionOutputs?.[output.name];
                const pinId = `${instanceId}-output-${output.name}`;

                return (
                  <div
                    key={output.node_id}
                    className="relative flex items-center"
                    onMouseEnter={() => setHoveredPin(pinId)}
                    onMouseLeave={() => setHoveredPin(null)}
                  >
                    {/* Pin Info */}
                    <div className="flex-1 bg-gray-700 rounded px-3 py-2 mr-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-white">{output.name}</span>
                        <span className="text-xs text-gray-400 font-mono">{output.type[0]}</span>
                      </div>

                      {/* Execution Value */}
                      {executionValue && (
                        <div className="mt-1 text-xs text-green-300 font-mono truncate" title={formatValue(executionValue.value)}>
                          {formatValue(executionValue.value)}
                        </div>
                      )}
                    </div>

                    {/* Output Handle */}
                    <Handle
                      type="source"
                      position={Position.Right}
                      id={output.node_id}
                      className="!bg-green-400 !w-3 !h-3 !border-2 !border-green-200 !-right-1.5"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error Display */}
        {executionError && (
          <div className="bg-red-900/50 border border-red-700 rounded px-3 py-2">
            <div className="text-xs text-red-300 font-semibold mb-1">ERROR</div>
            <div className="text-xs text-red-200">
              {executionError.message || JSON.stringify(executionError)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
