import React from 'react';
import { ExtractedDataModuleComponent } from '../modules/ExtractedDataModuleComponent';
import { Module } from '../modules/Module';
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

interface ModuleLayerProps {
  // Module data
  placedModules: PlacedModule[];
  connections: NodeConnection[];
  
  // Viewport state
  zoom: number;
  panOffset: { x: number; y: number };
  
  // Event handlers for modules
  onModuleMouseDown: (moduleId: string) => (e: React.MouseEvent) => void;
  onModuleDelete: (moduleId: string) => () => void;
  onModuleConfigChange: (moduleId: string) => (config: Record<string, unknown>) => void;
  
  // Event handlers for nodes
  onNodeClick: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => (e: React.MouseEvent) => void;
  onNodePositionUpdate: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, position: { x: number; y: number }) => void;
  
  // Node management handlers
  onAddInput: (moduleId: string) => void;
  onRemoveInput: (moduleId: string, inputIndex: number) => void;
  onAddOutput: (moduleId: string) => void;
  onRemoveOutput: (moduleId: string, outputIndex: number) => void;
  onNodeTypeChange: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: 'string' | 'number' | 'boolean' | 'datetime') => void;
  onNodeNameChange: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => void;
  
  // Helper functions
  getInputDisplayName: (moduleId: string, inputIndex: number) => string;
  canChangeType: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => boolean;
}

export const ModuleLayer: React.FC<ModuleLayerProps> = ({
  placedModules,
  connections,
  zoom,
  panOffset,
  onModuleMouseDown,
  onModuleDelete,
  onModuleConfigChange,
  onNodeClick,
  onNodePositionUpdate,
  onAddInput,
  onRemoveInput,
  onAddOutput,
  onRemoveOutput,
  onNodeTypeChange,
  onNodeNameChange,
  getInputDisplayName,
  canChangeType
}) => {
  return (
    <div style={{ position: 'relative', zIndex: 2 }}>
      {placedModules.map((placedModule) => {
        // Use ExtractedDataModuleComponent for extracted data modules
        if (placedModule.template.category === 'Extracted Data') {
          return (
            <ExtractedDataModuleComponent
              key={placedModule.id}
              moduleId={placedModule.id}
              template={placedModule.template}
              position={placedModule.position}
              config={placedModule.config}
              zoom={zoom}
              panOffset={panOffset}
              onMouseDown={onModuleMouseDown(placedModule.id)}
              onDelete={onModuleDelete(placedModule.id)}
              onConfigChange={onModuleConfigChange(placedModule.id)}
              onNodeClick={onNodeClick}
              onNodePositionUpdate={onNodePositionUpdate}
            />
          );
        }
        
        // Use Module for all other modules
        return (
          <Module
            key={placedModule.id}
            moduleId={placedModule.id}
            template={placedModule.template}
            position={placedModule.position}
            config={placedModule.config}
            nodes={placedModule.nodes}
            zoom={zoom}
            panOffset={panOffset}
            connections={connections}
            placedModules={placedModules}
            onMouseDown={onModuleMouseDown(placedModule.id)}
            onDelete={onModuleDelete(placedModule.id)}
            onConfigChange={onModuleConfigChange(placedModule.id)}
            onNodeClick={onNodeClick}
            onAddInput={onAddInput}
            onRemoveInput={onRemoveInput}
            onAddOutput={onAddOutput}
            onRemoveOutput={onRemoveOutput}
            onNodeTypeChange={onNodeTypeChange}
            onNodePositionUpdate={onNodePositionUpdate}
            onNameChange={onNodeNameChange}
            getInputDisplayName={getInputDisplayName}
            canChangeType={canChangeType}
          />
        );
      })}
    </div>
  );
};