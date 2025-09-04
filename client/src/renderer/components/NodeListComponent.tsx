import React from 'react';
import { NodeComponent } from './NodeComponent';

interface NodeState {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime';
  description: string;
  required: boolean;
}

interface NodeConnection {
  id: string;
  fromModuleId: string;
  fromOutputIndex: number;
  toModuleId: string;
  toInputIndex: number;
}

interface PlacedModule {
  id: string;
  template: any;
  position: { x: number; y: number };
  config: any;
  nodes: {
    inputs: any[];
    outputs: any[];
  };
}

interface NodeListComponentProps {
  moduleId: string;
  modulePosition?: { x: number; y: number }; // Add module position
  zoom?: number; // Add zoom level
  panOffset?: { x: number; y: number }; // Add pan offset
  connections?: NodeConnection[]; // Add connections
  placedModules?: PlacedModule[]; // Add placed modules
  isSidebarCollapsed?: boolean; // Add sidebar state for layout changes
  inputNodes: NodeState[];
  outputNodes: NodeState[];
  canAddInputs: boolean;
  canAddOutputs: boolean;
  canRemoveInputs: boolean;
  canRemoveOutputs: boolean;
  allowInputTypeConfiguration: boolean;
  allowOutputTypeConfiguration: boolean;
  onNodeClick?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => (e: React.MouseEvent) => void;
  onRemoveInput?: (moduleId: string, inputIndex: number) => void;
  onRemoveOutput?: (moduleId: string, outputIndex: number) => void;
  onAddInput?: (moduleId: string) => void;
  onAddOutput?: (moduleId: string) => void;
  onNodeTypeChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: 'string' | 'number' | 'boolean' | 'datetime') => void;
  onNodePositionUpdate?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, position: { x: number; y: number }) => void;
  onNameChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => void;
  getInputDisplayName?: (moduleId: string, nodeIndex: number) => string;
  canChangeType?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => boolean;
}

export const NodeListComponent: React.FC<NodeListComponentProps> = ({
  moduleId,
  modulePosition,
  zoom,
  panOffset,
  connections,
  placedModules,
  isSidebarCollapsed,
  inputNodes,
  outputNodes,
  canAddInputs,
  canAddOutputs,
  canRemoveInputs,
  canRemoveOutputs,
  allowInputTypeConfiguration,
  allowOutputTypeConfiguration,
  onNodeClick,
  onRemoveInput,
  onRemoveOutput,
  onAddInput,
  onAddOutput,
  onNodeTypeChange,
  onNodePositionUpdate,
  onNameChange,
  getInputDisplayName,
  canChangeType
}) => {
  // Calculate how many rows we need
  const inputsWithAdd = canAddInputs ? inputNodes.length + 1 : inputNodes.length;
  const outputsWithAdd = canAddOutputs ? outputNodes.length + 1 : outputNodes.length;
  const totalRows = Math.max(inputsWithAdd, outputsWithAdd, 1);

  return (
    <div className="border-t border-gray-700 bg-gray-800">
      {Array.from({ length: totalRows }, (_, rowIndex) => {
        const inputNode = inputNodes[rowIndex];
        const outputNode = outputNodes[rowIndex];
        const showAddInput = canAddInputs && rowIndex === inputNodes.length;
        const showAddOutput = canAddOutputs && rowIndex === outputNodes.length;

        return (
          <div key={`row-${rowIndex}`} className="flex border-b border-gray-700 last:border-b-0 min-h-12">
            {/* Input Half */}
            <div className="flex-1 flex items-center relative px-3 py-2">
              {inputNode ? (
                <NodeComponent
                  node={inputNode}
                  nodeType="input"
                  nodeIndex={rowIndex}
                  moduleId={moduleId}
                  modulePosition={modulePosition}
                  zoom={zoom}
                  panOffset={panOffset}
                  connections={connections}
                  placedModules={placedModules}
                  isSidebarCollapsed={isSidebarCollapsed}
                  canRemove={canRemoveInputs}
                  allowTypeConfiguration={allowInputTypeConfiguration}
                  onNodeClick={onNodeClick}
                  onRemove={onRemoveInput}
                  onTypeChange={onNodeTypeChange}
                  onPositionUpdate={onNodePositionUpdate}
                  onNameChange={onNameChange}
                  getInputDisplayName={getInputDisplayName}
                  canChangeType={canChangeType}
                />
              ) : showAddInput ? (
                <>
                  {/* Add Input Button */}
                  <div 
                    className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2"
                    style={{ zIndex: 10 }}
                  >
                    <button
                      className="w-5 h-5 rounded-full border-2 border-gray-600 bg-gray-700 hover:bg-gray-600 cursor-pointer hover:scale-110 transition-all flex items-center justify-center"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddInput?.(moduleId);
                      }}
                      title="Add Input"
                    >
                      <svg className="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                    </button>
                  </div>
                  <div className="ml-6 text-xs text-gray-500">Add input</div>
                </>
              ) : null}
            </div>

            {/* Output Half */}
            <div className="flex-1 flex items-center justify-end relative px-3 py-2">
              {outputNode ? (
                <NodeComponent
                  node={outputNode}
                  nodeType="output"
                  nodeIndex={rowIndex}
                  moduleId={moduleId}
                  modulePosition={modulePosition}
                  zoom={zoom}
                  panOffset={panOffset}
                  connections={connections}
                  placedModules={placedModules}
                  isSidebarCollapsed={isSidebarCollapsed}
                  canRemove={canRemoveOutputs}
                  allowTypeConfiguration={allowOutputTypeConfiguration}
                  onNodeClick={onNodeClick}
                  onRemove={onRemoveOutput}
                  onTypeChange={onNodeTypeChange}
                  onPositionUpdate={onNodePositionUpdate}
                  onNameChange={onNameChange}
                  getInputDisplayName={getInputDisplayName}
                  canChangeType={canChangeType}
                />
              ) : showAddOutput ? (
                <>
                  <div className="mr-6 text-xs text-gray-500">Add output</div>
                  {/* Add Output Button */}
                  <div 
                    className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2"
                    style={{ zIndex: 10 }}
                  >
                    <button
                      className="w-5 h-5 rounded-full border-2 border-gray-600 bg-gray-700 hover:bg-gray-600 cursor-pointer hover:scale-110 transition-all flex items-center justify-center"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddOutput?.(moduleId);
                      }}
                      title="Add Output"
                    >
                      <svg className="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                    </button>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
};