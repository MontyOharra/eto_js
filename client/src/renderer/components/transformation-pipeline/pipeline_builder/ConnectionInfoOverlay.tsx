import React from 'react';
import { Connection, ModuleInstance, NodePin, ModuleTemplate } from '../../../types/pipelineTypes';

interface ConnectionInfoOverlayProps {
  selectedConnectionId: string | null;
  connections: Connection[];
  modules: ModuleInstance[];
  moduleTemplates: ModuleTemplate[];
  onDelete: () => void;
  onClose: () => void;
}

export const ConnectionInfoOverlay: React.FC<ConnectionInfoOverlayProps> = ({
  selectedConnectionId,
  connections,
  modules,
  moduleTemplates,
  onDelete,
  onClose
}) => {
  if (!selectedConnectionId) return null;

  // Parse the connection ID to get the node IDs
  const [fromNodeId, toNodeId] = selectedConnectionId.split('-');

  // Find the actual connection
  const connection = connections.find(conn =>
    conn.from_node_id === fromNodeId && conn.to_node_id === toNodeId
  );

  if (!connection) return null;

  // Find the modules and nodes
  let fromModule: ModuleInstance | undefined;
  let fromNode: NodePin | undefined;
  let toModule: ModuleInstance | undefined;
  let toNode: NodePin | undefined;

  for (const module of modules) {
    // Check outputs for the from node
    const outputNode = module.outputs.find(n => n.node_id === connection.from_node_id);
    if (outputNode) {
      fromModule = module;
      fromNode = outputNode;
    }

    // Check inputs for the to node
    const inputNode = module.inputs.find(n => n.node_id === connection.to_node_id);
    if (inputNode) {
      toModule = module;
      toNode = inputNode;
    }
  }

  if (!fromModule || !fromNode || !toModule || !toNode) return null;

  // Get module template by ref
  const getModuleTemplate = (moduleRef: string): ModuleTemplate | undefined => {
    const [moduleId] = moduleRef.split(':');
    return moduleTemplates.find(t => t.id === moduleId);
  };

  const fromTemplate = getModuleTemplate(fromModule.module_ref);
  const toTemplate = getModuleTemplate(toModule.module_ref);

  if (!fromTemplate || !toTemplate) return null;

  return (
    <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-30">
      <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 p-3 min-w-[400px] max-w-[600px]">
        {/* Header with close button */}
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold text-gray-300">Connection</h3>
          <button
            onClick={onClose}
            className="w-4 h-4 text-gray-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <svg className="w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Horizontal Connection Layout */}
        <div className="flex items-center justify-between gap-4">
          {/* From Module */}
          <div className="flex items-center gap-2 flex-1">
            <div
              className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: fromTemplate.color }}
            >
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs text-white font-medium truncate">{fromTemplate.title}</div>
              <div className="text-xs text-gray-400 truncate">{fromNode.name} ({fromNode.type})</div>
            </div>
          </div>

          {/* Arrow */}
          <div className="flex-shrink-0 px-2">
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </div>

          {/* To Module */}
          <div className="flex items-center gap-2 flex-1">
            <div
              className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: toTemplate.color }}
            >
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs text-white font-medium truncate">{toTemplate.title}</div>
              <div className="text-xs text-gray-400 truncate">{toNode.name} ({toNode.type})</div>
            </div>
          </div>

          {/* Delete Button */}
          <button
            onClick={onDelete}
            className="px-2 py-1 bg-red-600 hover:bg-red-700 text-white text-xs font-medium rounded transition-colors flex items-center gap-1 flex-shrink-0"
            title="Delete Connection"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <span>Delete</span>
          </button>
        </div>
      </div>
    </div>
  );
};