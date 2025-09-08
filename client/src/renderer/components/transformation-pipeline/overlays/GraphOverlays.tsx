import React from 'react';
import { BaseModuleTemplate } from '../../../types/modules';

// Types
interface NodeState {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime';
  description: string;
  required: boolean;
}

interface ModuleNodeState {
  inputs: NodeState[];
  outputs: NodeState[];
}

interface PlacedModule {
  id: string;
  template: BaseModuleTemplate;
  position: { x: number; y: number };
  config: Record<string, any>;
  nodes: ModuleNodeState;
}

interface NodeConnection {
  id: string;
  fromModuleId: string;
  fromOutputIndex: number;
  toModuleId: string;
  toInputIndex: number;
}

interface StartingConnection {
  moduleId: string;
  type: 'input' | 'output';
  index: number;
}

interface GraphOverlaysProps {
  // State
  connections: NodeConnection[];
  selectedConnectionId: string | null;
  startingConnection: StartingConnection | null;
  placedModules: PlacedModule[];
  zoom: number;
  isDraggingModule: boolean;
  
  // Event handlers
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
  onConnectionDelete: (connectionId: string) => void;
  onAnalyzePipeline?: () => void;
  onPrintObjects?: () => void;
  onGetBaseModules?: () => void;
  
  // Helper functions
  getTypeColor: (type: string) => string;
}

export const GraphOverlays: React.FC<GraphOverlaysProps> = ({
  connections,
  selectedConnectionId,
  startingConnection,
  placedModules,
  zoom,
  isDraggingModule,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  onConnectionDelete,
  onAnalyzePipeline,
  onPrintObjects,
  onGetBaseModules,
  getTypeColor
}) => {
  return (
    <>
      {/* Pipeline Analysis Controls - Top Left */}
      <div className="absolute top-4 left-4 z-20 flex flex-col gap-2">
        <button
          onClick={onAnalyzePipeline}
          disabled={isDraggingModule}
          className={`px-4 py-2 rounded-lg shadow-lg border transition-colors flex items-center gap-2 ${
            isDraggingModule
              ? 'bg-gray-700 border-gray-600 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 border-blue-500 text-white hover:bg-blue-700'
          }`}
          title={isDraggingModule ? "Cannot analyze while dragging" : "Analyze Pipeline"}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
          </svg>
          <span className="text-sm font-medium">Analyze Pipeline</span>
        </button>
        
        <button
          onClick={onPrintObjects}
          disabled={isDraggingModule}
          className={`px-4 py-2 rounded-lg shadow-lg border transition-colors flex items-center gap-2 ${
            isDraggingModule
              ? 'bg-gray-700 border-gray-600 text-gray-500 cursor-not-allowed'
              : 'bg-gray-600 border-gray-500 text-white hover:bg-gray-700'
          }`}
          title={isDraggingModule ? "Cannot print while dragging" : "Print Objects to Console"}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-sm font-medium">Print Objects</span>
        </button>
        
        <button
          onClick={onGetBaseModules}
          disabled={isDraggingModule}
          className={`px-4 py-2 rounded-lg shadow-lg border transition-colors flex items-center gap-2 ${
            isDraggingModule
              ? 'bg-gray-700 border-gray-600 text-gray-500 cursor-not-allowed'
              : 'bg-green-600 border-green-500 text-white hover:bg-green-700'
          }`}
          title={isDraggingModule ? "Cannot fetch while dragging" : "Get Base Modules from Database"}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
          <span className="text-sm font-medium">Get Base Modules</span>
        </button>
      </div>

      {/* Zoom Controls - Top Right */}
      <div className="absolute top-4 right-4 z-20 flex flex-col bg-gray-800 rounded-lg shadow-lg border border-gray-700">
        <button
          onClick={isDraggingModule ? undefined : onZoomIn}
          disabled={isDraggingModule}
          className={`w-10 h-10 flex items-center justify-center transition-colors rounded-t-lg border-b border-gray-700 ${
            isDraggingModule 
              ? 'text-gray-500 cursor-not-allowed' 
              : 'text-white hover:bg-gray-700'
          }`}
          title={isDraggingModule ? "Cannot zoom while dragging" : "Zoom In"}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </button>
        
        <div className="w-10 h-8 flex items-center justify-center text-xs text-gray-400 border-b border-gray-700">
          {Math.round(zoom * 100)}%
        </div>
        
        <button
          onClick={isDraggingModule ? undefined : onZoomOut}
          disabled={isDraggingModule}
          className={`w-10 h-10 flex items-center justify-center transition-colors border-b border-gray-700 ${
            isDraggingModule 
              ? 'text-gray-500 cursor-not-allowed' 
              : 'text-white hover:bg-gray-700'
          }`}
          title={isDraggingModule ? "Cannot zoom while dragging" : "Zoom Out"}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 12H6" />
          </svg>
        </button>
        
        <button
          onClick={isDraggingModule ? undefined : onResetZoom}
          disabled={isDraggingModule}
          className={`w-10 h-10 flex items-center justify-center transition-colors rounded-b-lg ${
            isDraggingModule 
              ? 'text-gray-500 cursor-not-allowed' 
              : 'text-white hover:bg-gray-700'
          }`}
          title={isDraggingModule ? "Cannot fit while dragging" : "Fit All to View"}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {/* Top-left corner */}
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 3H3v4" />
            {/* Top-right corner */}
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 3h4v4" />
            {/* Bottom-left corner */}
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21H3v-4" />
            {/* Bottom-right corner */}
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 21h4v-4" />
          </svg>
        </button>
      </div>

      {/* Connection Info Panel - Bottom */}
      {selectedConnectionId && (() => {
        const selectedConnection = connections.find(conn => conn.id === selectedConnectionId);
        if (!selectedConnection) return null;
        
        const outputModule = placedModules.find(m => m.id === selectedConnection.fromModuleId);
        const inputModule = placedModules.find(m => m.id === selectedConnection.toModuleId);
        
        if (!outputModule || !inputModule) return null;
        
        const outputNode = outputModule.nodes.outputs[selectedConnection.fromOutputIndex];
        const inputNode = inputModule.nodes.inputs[selectedConnection.toInputIndex];
        
        if (!outputNode || !inputNode) return null;
        
        const connectionType = outputNode.type;
        const connectionColor = getTypeColor(connectionType);
        
        return (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-30">
            <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-600 px-4 py-3 min-w-96">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {/* Connection Type Indicator */}
                  <div 
                    className="w-4 h-4 rounded-full border-2 border-gray-600"
                    style={{ backgroundColor: connectionColor }}
                    title={`${connectionType} connection`}
                  />
                  
                  {/* Connection Info */}
                  <div className="text-white text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-300 font-medium">{outputModule.template.name}</span>
                      <span className="text-blue-400 text-xs">({outputNode.name})</span>
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                      </svg>
                      <span className="text-gray-300 font-medium">{inputModule.template.name}</span>
                      <span className="text-blue-400 text-xs">({inputNode.name})</span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      Type: <span className="text-blue-300 capitalize">{connectionType}</span>
                    </div>
                  </div>
                </div>
                
                {/* Delete Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onConnectionDelete(selectedConnectionId);
                  }}
                  className="w-8 h-8 flex items-center justify-center text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded transition-colors"
                  title="Delete connection"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </>
  );
};