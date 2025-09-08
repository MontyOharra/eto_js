import React, { useState, useRef, useEffect, useCallback } from 'react';
import { BaseModuleTemplate } from '../../types/modules';
import { mockExtractedFields } from '../../data/testModules';
import { InputDefiner, OutputDefiner } from '../../types/inputOutputDefiners';
import { GraphCanvas } from './canvas/GraphCanvas';
import { ModuleLayer } from './layers/ModuleLayer';
import { ConnectionLayer } from './layers/ConnectionLayer';
import { GraphOverlays } from './overlays/GraphOverlays';
import { InputOutputDefinerComponent } from './module-builder/InputOutputDefinerComponent';
import { InputCollectionModal } from './modals/InputCollectionModal';
import { apiClient } from '../../services/api';
import { analyzePipelineWithSteps } from '../../services/transformationPipelineApi';

// Types (extracted from original file)
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

interface TransformationGraphProps {
  modules: BaseModuleTemplate[];
  selectedModuleTemplate: BaseModuleTemplate | null;
  onModuleSelect: (module: BaseModuleTemplate | null) => void;
  // Optional props for custom module builder
  enableInputOutputDefiners?: boolean;
  inputDefiners?: InputDefiner[];
  outputDefiners?: OutputDefiner[];
  onInputDefinersChange?: (definers: InputDefiner[]) => void;
  onOutputDefinersChange?: (definers: OutputDefiner[]) => void;
}

export const TransformationGraph: React.FC<TransformationGraphProps> = ({
  modules,
  selectedModuleTemplate,
  onModuleSelect,
  enableInputOutputDefiners = false,
  inputDefiners = [],
  outputDefiners = [],
  onInputDefinersChange,
  onOutputDefinersChange
}) => {
  // Graph viewport state
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  
  // Refs to access current zoom and pan values without causing useEffect re-creation
  const zoomRef = useRef(zoom);
  const panOffsetRef = useRef(panOffset);
  
  useEffect(() => { zoomRef.current = zoom; }, [zoom]);
  useEffect(() => { panOffsetRef.current = panOffset; }, [panOffset]);

  // Canvas dragging state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [dragStartOffset, setDragStartOffset] = useState({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLDivElement>(null);

  // Module state
  const [placedModules, setPlacedModules] = useState<PlacedModule[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  
  // Input/Output Definer state (for custom module builder)
  const [selectedDefinerId, setSelectedDefinerId] = useState<string | null>(null);
  
  // Module placement and dragging
  const [isPlacingModule, setIsPlacingModule] = useState(false);
  
  // Module dragging state
  const [isDraggingModule, setIsDraggingModule] = useState(false);
  const [draggedModuleId, setDraggedModuleId] = useState<string | null>(null);
  const [moduleDragOffset, setModuleDragOffset] = useState({ x: 0, y: 0 });

  // Connection state
  const [connections, setConnections] = useState<NodeConnection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<string | null>(null);
  const [startingConnection, setStartingConnection] = useState<StartingConnection | null>(null);

  // Modal state
  const [isInputModalOpen, setIsInputModalOpen] = useState(false);
  const [currentExecutionData, setCurrentExecutionData] = useState<{
    processingModules: any[];
    inputDefinitions: any[];
    outputDefinitions: any[];
    pipelineConnections: any[];
  } | null>(null);
  const [currentMousePosition, setCurrentMousePosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Node position tracking
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});

  // Get node type color
  const getTypeColor = (type: string): string => {
    switch (type) {
      case 'string': return '#3B82F6'; // Blue
      case 'number': return '#EF4444'; // Red  
      case 'boolean': return '#10B981'; // Green
      case 'datetime': return '#8B5CF6'; // Purple
      default: return '#6B7280'; // Gray
    }
  };

  // Get node type from module state
  const getNodeType = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number): string => {
    const module = placedModules.find(m => m.id === moduleId);
    if (!module) return 'string';
    
    const nodeList = nodeType === 'input' ? module.nodes.inputs : module.nodes.outputs;
    const node = nodeList[nodeIndex];
    return node?.type || 'string';
  };

  // Helper function to initialize module nodes from template
  const initializeModuleNodes = (template: BaseModuleTemplate, config: Record<string, unknown>, moduleId?: string): ModuleNodeState => {
    let inputs: NodeState[] = [];
    let outputs: NodeState[] = [];
    
    // Generate unique timestamp for this module instance if no moduleId provided
    const instanceId = moduleId || `${template.id}_${Date.now()}`;
    
    // Use generateNodes if available for dynamic modules
    if (template.generateNodes) {
      const generated = template.generateNodes(config);
      inputs = generated.inputs.map((input, index) => ({
        id: `${instanceId}_input_${index}`,
        name: input.name || `Input ${index + 1}`,
        type: input.type,
        description: input.description,
        required: input.required
      }));
      outputs = generated.outputs.map((output, index) => ({
        id: `${instanceId}_output_${index}`,
        name: output.name || `Output ${index + 1}`,
        type: output.type,
        description: output.description,
        required: output.required || false
      }));
    } else {
      // Use template nodes for static modules
      inputs = template.inputs.map((input, index) => ({
        id: `${instanceId}_input_${index}`,
        name: input.name || `Input ${index + 1}`,
        type: input.type,
        description: input.description,
        required: input.required
      }));
      outputs = template.outputs.map((output, index) => ({
        id: `${instanceId}_output_${index}`,
        name: output.name || `Output ${index + 1}`,
        type: output.type,
        description: output.description,
        required: output.required || false
      }));
    }
    
    return { inputs, outputs };
  };

  // Helper function to get display name for an input based on connections
  const getInputDisplayName = (moduleId: string, inputIndex: number): string => {
    // Find connection to this input
    const connection = connections.find(conn => 
      conn.toModuleId === moduleId && conn.toInputIndex === inputIndex
    );
    
    if (!connection) {
      return "Not connected";
    }
    
    // Find the source module and output
    const sourceModule = placedModules.find(m => m.id === connection.fromModuleId);
    if (!sourceModule) {
      return "Not connected";
    }
    
    const sourceOutput = sourceModule.nodes.outputs[connection.fromOutputIndex];
    return sourceOutput?.name || "Unknown output";
  };

  // Helper function to check if a node allows type configuration
  const getNodeTypeConfigAllowed = (moduleId: string, nodeType: 'input' | 'output'): boolean => {
    const module = placedModules.find(m => m.id === moduleId);
    if (!module) return false;

    if (nodeType === 'input') {
      // Check both dynamic and static type configuration support
      return (
        module.template.dynamicInputs?.allowTypeConfiguration || 
        module.template.allowInputTypeConfig || 
        false
      );
    } else {
      // Check both dynamic and static type configuration support
      return (
        module.template.dynamicOutputs?.allowTypeConfiguration || 
        module.template.allowOutputTypeConfig || 
        false
      );
    }
  };

  // Helper function to check if a node can change type based on connections
  const canNodeChangeType = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number): boolean => {
    // First check if this node itself allows type configuration
    if (!getNodeTypeConfigAllowed(moduleId, nodeType)) {
      return false;
    }
    
    // Check if this is an I/O definer - they always allow type changes
    const module = placedModules.find(m => m.id === moduleId);
    const isIODefiner = module?.template.category === 'Module Definers';
    
    if (isIODefiner) {
      return true; // I/O definers can always change type
    }

    if (nodeType === 'input') {
      // Check if input is connected
      const connection = connections.find(conn => 
        conn.toModuleId === moduleId && conn.toInputIndex === nodeIndex
      );
      
      if (!connection) {
        return true; // No connection, can change type
      }
      
      // Check if the connected output is from an I/O definer or allows type configuration
      const connectedModule = placedModules.find(m => m.id === connection.fromModuleId);
      const isConnectedToIODefiner = connectedModule?.template.category === 'Module Definers';
      
      if (isConnectedToIODefiner) {
        return true; // Connected to I/O definer, can change type
      }
      
      // Check if the connected output allows type configuration
      return getNodeTypeConfigAllowed(connection.fromModuleId, 'output');
    } else {
      // For outputs, check all connected inputs
      const outputConnections = connections.filter(conn => 
        conn.fromModuleId === moduleId && conn.fromOutputIndex === nodeIndex
      );
      
      if (outputConnections.length === 0) {
        return true; // No connections, can change type
      }
      
      // All connected inputs must allow type configuration OR be I/O definers
      return outputConnections.every(connection => {
        const connectedModule = placedModules.find(m => m.id === connection.toModuleId);
        const isConnectedToIODefiner = connectedModule?.template.category === 'Module Definers';
        
        if (isConnectedToIODefiner) {
          return true; // Connected to I/O definer, can change type
        }
        
        return getNodeTypeConfigAllowed(connection.toModuleId, 'input');
      });
    }
  };

  // Add input node
  const handleAddInput = (moduleId: string) => {
    setPlacedModules(prev => prev.map(module => {
      if (module.id !== moduleId || !module.template.dynamicInputs?.enabled) return module;
      
      const currentInputs = module.nodes.inputs;
      const maxInputs = module.template.dynamicInputs.maxNodes;
      
      if (maxInputs && currentInputs.length >= maxInputs) return module;
      
      const newIndex = currentInputs.length + 1;
      const template = module.template.dynamicInputs.defaultTemplate;
      
      const newInput: NodeState = {
        id: `${module.id}_input_${newIndex}`,
        name: template.name.replace('{{index}}', newIndex.toString()),
        type: template.type,
        description: template.description.replace('{{index}}', newIndex.toString()),
        required: template.required || false
      };
      
      // Add default config for new input's type if it has dynamicType
      const newConfig = { ...module.config };
      if (template.dynamicType) {
        const configKey = template.dynamicType.configKey.replace('{{index}}', newIndex.toString());
        newConfig[configKey] = newInput.type;
      }
      
      return {
        ...module,
        config: newConfig,
        nodes: {
          ...module.nodes,
          inputs: [...currentInputs, newInput]
        }
      };
    }));
  };

  // Remove input node
  const handleRemoveInput = (moduleId: string, inputIndex: number) => {
    setPlacedModules(prev => prev.map(module => {
      if (module.id !== moduleId || !module.template.dynamicInputs?.enabled) return module;
      
      const currentInputs = module.nodes.inputs;
      const minInputs = module.template.dynamicInputs.minNodes || 0;
      
      if (currentInputs.length <= minInputs) return module;
      
      const newInputs = currentInputs.filter((_, index) => index !== inputIndex);
      
      return {
        ...module,
        nodes: {
          ...module.nodes,
          inputs: newInputs
        }
      };
    }));
    
    // Remove connections associated with the deleted input node
    setConnections(prev => {
      const connectionsToRemove = prev.filter(connection => 
        connection.toModuleId === moduleId && connection.toInputIndex === inputIndex
      );
      
      // Clear selection if selected connection is being deleted
      connectionsToRemove.forEach(connection => {
        if (selectedConnectionId === connection.id) {
          setSelectedConnectionId(null);
        }
      });
      
      return prev.filter(connection => 
        !(connection.toModuleId === moduleId && connection.toInputIndex === inputIndex)
      );
    });
    
    // Update connection indices for inputs that moved up after deletion
    setConnections(prev => prev.map(connection => {
      if (connection.toModuleId === moduleId && connection.toInputIndex > inputIndex) {
        return {
          ...connection,
          toInputIndex: connection.toInputIndex - 1
        };
      }
      return connection;
    }));
    
    // Clean up node position registry for deleted input and shift remaining indices
    setNodePositions(prev => {
      const newPositions = { ...prev };
      
      // Remove the deleted input's position
      delete newPositions[`${moduleId}-input-${inputIndex}`];
      
      // Shift higher-indexed inputs down by 1
      Object.keys(newPositions).forEach(key => {
        const match = key.match(new RegExp(`^${moduleId}-input-(\\d+)$`));
        if (match) {
          const index = parseInt(match[1]);
          if (index > inputIndex) {
            const newKey = `${moduleId}-input-${index - 1}`;
            newPositions[newKey] = newPositions[key];
            delete newPositions[key];
          }
        }
      });
      
      return newPositions;
    });
  };

  // Add output node
  const handleAddOutput = (moduleId: string) => {
    setPlacedModules(prev => prev.map(module => {
      if (module.id !== moduleId || !module.template.dynamicOutputs?.enabled) return module;
      
      const currentOutputs = module.nodes.outputs;
      const maxOutputs = module.template.dynamicOutputs.maxNodes;
      
      if (maxOutputs && currentOutputs.length >= maxOutputs) return module;
      
      const newIndex = currentOutputs.length + 1;
      const template = module.template.dynamicOutputs.defaultTemplate;
      
      const newOutput: NodeState = {
        id: `${module.id}_output_${newIndex}`,
        name: `Output ${newIndex}`,
        type: template.type,
        description: template.description.replace('{{index}}', newIndex.toString()),
        required: template.required || false
      };
      
      // Add default config for new output's type if it has dynamicType
      const newConfig = { ...module.config };
      if (template.dynamicType) {
        const configKey = template.dynamicType.configKey.replace('{{index}}', newIndex.toString());
        newConfig[configKey] = newOutput.type;
      }
      
      return {
        ...module,
        config: newConfig,
        nodes: {
          ...module.nodes,
          outputs: [...currentOutputs, newOutput]
        }
      };
    }));
  };

  // Remove output node
  const handleRemoveOutput = (moduleId: string, outputIndex: number) => {
    setPlacedModules(prev => prev.map(module => {
      if (module.id !== moduleId || !module.template.dynamicOutputs?.enabled) return module;
      
      const currentOutputs = module.nodes.outputs;
      const minOutputs = module.template.dynamicOutputs.minNodes || 0;
      
      if (currentOutputs.length <= minOutputs) return module;
      
      const newOutputs = currentOutputs.filter((_, index) => index !== outputIndex);
      
      return {
        ...module,
        nodes: {
          ...module.nodes,
          outputs: newOutputs
        }
      };
    }));
    
    // Remove connections associated with the deleted output node
    setConnections(prev => {
      const connectionsToRemove = prev.filter(connection => 
        connection.fromModuleId === moduleId && connection.fromOutputIndex === outputIndex
      );
      
      // Clear selection if selected connection is being deleted
      connectionsToRemove.forEach(connection => {
        if (selectedConnectionId === connection.id) {
          setSelectedConnectionId(null);
        }
      });
      
      return prev.filter(connection => 
        !(connection.fromModuleId === moduleId && connection.fromOutputIndex === outputIndex)
      );
    });
    
    // Update connection indices for outputs that moved up after deletion
    setConnections(prev => prev.map(connection => {
      if (connection.fromModuleId === moduleId && connection.fromOutputIndex > outputIndex) {
        return {
          ...connection,
          fromOutputIndex: connection.fromOutputIndex - 1
        };
      }
      return connection;
    }));
    
    // Clean up node position registry for deleted output and shift remaining indices
    setNodePositions(prev => {
      const newPositions = { ...prev };
      
      // Remove the deleted output's position
      delete newPositions[`${moduleId}-output-${outputIndex}`];
      
      // Shift higher-indexed outputs down by 1
      Object.keys(newPositions).forEach(key => {
        const match = key.match(new RegExp(`^${moduleId}-output-(\\d+)$`));
        if (match) {
          const index = parseInt(match[1]);
          if (index > outputIndex) {
            const newKey = `${moduleId}-output-${index - 1}`;
            newPositions[newKey] = newPositions[key];
            delete newPositions[key];
          }
        }
      });
      
      return newPositions;
    });
  };

  // Handle node type change
  const handleNodeTypeChange = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: 'string' | 'number' | 'boolean' | 'datetime') => {
    // Check if the node can change type
    if (!canNodeChangeType(moduleId, nodeType, nodeIndex)) {
      return;
    }

    setPlacedModules(prev => {
      let updatedModules = [...prev];
      
      // Update the original node
      updatedModules = updatedModules.map(module => {
        if (module.id !== moduleId) return module;
        
        const nodeList = nodeType === 'input' ? module.nodes.inputs : module.nodes.outputs;
        const updatedNodes = nodeList.map((node, index) => 
          index === nodeIndex ? { ...node, type: newType } : node
        );
        
        // For input/output definers, also update the data_type config
        let updatedConfig = module.config;
        if (module.template.category === 'Module Definers') {
          updatedConfig = { ...module.config, data_type: newType };
        }

        return {
          ...module,
          config: updatedConfig,
          nodes: {
            ...module.nodes,
            [nodeType === 'input' ? 'inputs' : 'outputs']: updatedNodes
          }
        };
      });

      // Synchronize connected nodes if they allow type configuration or are I/O definers
      if (nodeType === 'input') {
        // Find connected output and update its type if it allows configuration or is an I/O definer
        const connection = connections.find(conn => 
          conn.toModuleId === moduleId && conn.toInputIndex === nodeIndex
        );
        
        if (connection) {
          const connectedModule = updatedModules.find(m => m.id === connection.fromModuleId);
          const isConnectedIODefiner = connectedModule?.template.category === 'Module Definers';
          const allowsTypeConfig = getNodeTypeConfigAllowed(connection.fromModuleId, 'output');
          
          if (isConnectedIODefiner || allowsTypeConfig) {
            updatedModules = updatedModules.map(module => {
              if (module.id !== connection.fromModuleId) return module;
              
              const updatedOutputs = module.nodes.outputs.map((node, index) => 
                index === connection.fromOutputIndex ? { ...node, type: newType } : node
              );
              
              return {
                ...module,
                nodes: {
                  ...module.nodes,
                  outputs: updatedOutputs
                }
              };
            });
          }
        }
      } else {
        // Find all connected inputs and update their types if they allow configuration or are I/O definers
        const outputConnections = connections.filter(conn => 
          conn.fromModuleId === moduleId && conn.fromOutputIndex === nodeIndex
        );
        
        outputConnections.forEach(connection => {
          const connectedModule = updatedModules.find(m => m.id === connection.toModuleId);
          const isConnectedIODefiner = connectedModule?.template.category === 'Module Definers';
          const allowsTypeConfig = getNodeTypeConfigAllowed(connection.toModuleId, 'input');
          
          if (isConnectedIODefiner || allowsTypeConfig) {
            updatedModules = updatedModules.map(module => {
              if (module.id !== connection.toModuleId) return module;
              
              const updatedInputs = module.nodes.inputs.map((node, index) => 
                index === connection.toInputIndex ? { ...node, type: newType } : node
              );
              
              return {
                ...module,
                nodes: {
                  ...module.nodes,
                  inputs: updatedInputs
                }
              };
            });
          }
        });
      }

      return updatedModules;
    });
  };

  // Handle node name changes for inputs and outputs
  const handleNodeNameChange = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => {
    setPlacedModules(prev => prev.map(module => {
      if (module.id !== moduleId) return module;
      
      if (nodeType === 'input') {
        const updatedInputs = module.nodes.inputs.map((node, index) => 
          index === nodeIndex ? { ...node, name: newName } : node
        );
        
        return {
          ...module,
          nodes: {
            ...module.nodes,
            inputs: updatedInputs
          }
        };
      } else {
        const updatedOutputs = module.nodes.outputs.map((node, index) => 
          index === nodeIndex ? { ...node, name: newName } : node
        );
        
        return {
          ...module,
          nodes: {
            ...module.nodes,
            outputs: updatedOutputs
          }
        };
      }
    }));
  };

  // Handle node position updates from DOM measurements
  const handleNodePositionUpdate = useCallback((moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, position: { x: number; y: number }) => {
    const nodeKey = `${moduleId}-${nodeType}-${nodeIndex}`;
    setNodePositions(prev => ({
      ...prev,
      [nodeKey]: position
    }));
  }, []);

  // Handle connection selection
  const handleConnectionClick = (connectionId: string) => (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    
    // Toggle selection
    if (selectedConnectionId === connectionId) {
      setSelectedConnectionId(null);
    } else {
      setSelectedConnectionId(connectionId);
    }
  };

  // Handle connection deletion
  const handleConnectionDelete = (connectionId: string) => {
    // Find the connection being deleted to check if it involves I/O definers
    const connectionToDelete = connections.find(conn => conn.id === connectionId);
    
    if (connectionToDelete) {
      const fromModule = placedModules.find(m => m.id === connectionToDelete.fromModuleId);
      const toModule = placedModules.find(m => m.id === connectionToDelete.toModuleId);
      const isFromIODefiner = fromModule?.template.category === 'Module Definers';
      const isToIODefiner = toModule?.template.category === 'Module Definers';
      
      // Update I/O definer types back to default when connection is removed
      if (isFromIODefiner || isToIODefiner) {
        setPlacedModules(prevModules => {
          return prevModules.map(module => {
            if (isFromIODefiner && module.id === connectionToDelete.fromModuleId) {
              // Reset output node type to undefined (I/O definers start undefined)
              const updatedOutputs = module.nodes.outputs.map((node, idx) => 
                idx === connectionToDelete.fromOutputIndex ? { ...node, type: 'undefined' } : node
              );
              return { ...module, nodes: { ...module.nodes, outputs: updatedOutputs } };
            }
            
            if (isToIODefiner && module.id === connectionToDelete.toModuleId) {
              // Reset input node type to undefined (I/O definers start undefined)
              const updatedInputs = module.nodes.inputs.map((node, idx) => 
                idx === connectionToDelete.toInputIndex ? { ...node, type: 'undefined' } : node
              );
              return { ...module, nodes: { ...module.nodes, inputs: updatedInputs } };
            }
            
            return module;
          });
        });
      }
    }
    
    setConnections(prev => prev.filter(connection => connection.id !== connectionId));
    setSelectedConnectionId(null);
  };


  // Zoom utility functions
  const zoomIn = () => {
    if (!canvasRef.current) return;
    
    const canvasRect = canvasRef.current.getBoundingClientRect();
    // Calculate center of viewport in screen coordinates (same as wheel zoom)
    const centerX = canvasRect.width / 2;
    const centerY = canvasRect.height / 2;
    
    // Use same approach as wheel zoom with current state values
    const currentZoom = zoomRef.current;
    const currentPanOffset = panOffsetRef.current;
    
    const newZoom = Math.min(currentZoom * 1.2, 3); // Max zoom 3x
    
    if (newZoom !== currentZoom) {
      // Calculate pan offset to zoom towards center (same math as wheel zoom)
      const zoomRatio = newZoom / currentZoom;
      const newPanX = centerX - (centerX - currentPanOffset.x) * zoomRatio;
      const newPanY = centerY - (centerY - currentPanOffset.y) * zoomRatio;
      
      setZoom(newZoom);
      setPanOffset({ x: newPanX, y: newPanY });
    }
  };

  const zoomOut = () => {
    if (!canvasRef.current) return;
    
    const canvasRect = canvasRef.current.getBoundingClientRect();
    // Calculate center of viewport in screen coordinates (same as wheel zoom)
    const centerX = canvasRect.width / 2;
    const centerY = canvasRect.height / 2;
    
    // Use same approach as wheel zoom with current state values
    const currentZoom = zoomRef.current;
    const currentPanOffset = panOffsetRef.current;
    
    const newZoom = Math.max(currentZoom / 1.2, 0.1); // Min zoom 0.1x
    
    if (newZoom !== currentZoom) {
      // Calculate pan offset to zoom towards center (same math as wheel zoom)
      const zoomRatio = newZoom / currentZoom;
      const newPanX = centerX - (centerX - currentPanOffset.x) * zoomRatio;
      const newPanY = centerY - (centerY - currentPanOffset.y) * zoomRatio;
      
      setZoom(newZoom);
      setPanOffset({ x: newPanX, y: newPanY });
    }
  };

  const resetZoom = () => {
    if (!canvasRef.current) return;
    
    // If no modules or definers, just reset to origin
    if (placedModules.length === 0 && inputDefiners.length === 0 && outputDefiners.length === 0) {
      setZoom(1);
      setPanOffset({ x: 0, y: 0 });
      return;
    }
    
    // Calculate bounding box of all modules
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    
    // Estimate module dimensions (modules are typically ~240-320px wide, ~200-300px tall)
    const moduleWidth = 280;
    const moduleHeight = 250;
    
    // Include placed modules in bounding box
    placedModules.forEach(module => {
      const left = module.position.x - moduleWidth / 2;
      const right = module.position.x + moduleWidth / 2;
      const top = module.position.y;
      const bottom = module.position.y + moduleHeight;
      
      minX = Math.min(minX, left);
      minY = Math.min(minY, top);
      maxX = Math.max(maxX, right);
      maxY = Math.max(maxY, bottom);
    });
    
    // Include input/output definers in bounding box
    const definerWidth = 200;
    const definerHeight = 100;
    
    [...inputDefiners, ...outputDefiners].forEach(definer => {
      const left = definer.position.x - definerWidth / 2;
      const right = definer.position.x + definerWidth / 2;
      const top = definer.position.y;
      const bottom = definer.position.y + definerHeight;
      
      minX = Math.min(minX, left);
      minY = Math.min(minY, top);
      maxX = Math.max(maxX, right);
      maxY = Math.max(maxY, bottom);
    });
    
    // If we couldn't calculate a valid bounding box, fallback to origin
    if (minX === Infinity || minY === Infinity || maxX === -Infinity || maxY === -Infinity) {
      setZoom(1);
      setPanOffset({ x: 0, y: 0 });
      return;
    }
    
    // Add padding around the modules
    const padding = 100;
    minX -= padding;
    minY -= padding;
    maxX += padding;
    maxY += padding;
    
    // Calculate bounding box dimensions
    const boundingWidth = maxX - minX;
    const boundingHeight = maxY - minY;
    
    // Get canvas dimensions
    const canvasRect = canvasRef.current.getBoundingClientRect();
    const canvasWidth = canvasRect.width;
    const canvasHeight = canvasRect.height;
    
    // Calculate zoom level to fit all modules with some padding
    const zoomX = canvasWidth / boundingWidth;
    const zoomY = canvasHeight / boundingHeight;
    const newZoom = Math.min(zoomX, zoomY, 1.5); // Cap at 1.5x to avoid over-zooming
    
    // Calculate center of bounding box
    const boundingCenterX = (minX + maxX) / 2;
    const boundingCenterY = (minY + maxY) / 2;
    
    // Calculate pan offset to center the bounding box
    const newPanX = canvasWidth / 2 - boundingCenterX * newZoom;
    const newPanY = canvasHeight / 2 - boundingCenterY * newZoom;
    
    // Apply the new zoom and pan
    setZoom(newZoom);
    setPanOffset({ x: newPanX, y: newPanY });
  };

  // Add mouse tracking for connection preview
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (startingConnection && canvasRef.current) {
        const canvasRect = canvasRef.current.getBoundingClientRect();
        const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
        const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
        setCurrentMousePosition({ x: mouseX, y: mouseY });
      }
    };

    if (startingConnection) {
      document.addEventListener('mousemove', handleMouseMove);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
      };
    }
  }, [startingConnection, panOffset, zoom]);

  // Handle mouse down for canvas - either place module or start canvas drag
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left mouse button
    
    // If module is selected, start placement
    if (selectedModuleTemplate) {
      handleModulePlacementStart(e);
      return;
    }
    
    // Cancel any active connection when clicking empty canvas
    if (startingConnection) {
      setStartingConnection(null);
      return;
    }
    
    // Deselect any selected module or connection when clicking empty canvas
    setSelectedModuleId(null);
    setSelectedConnectionId(null);
    
    // Only start canvas dragging if no module is currently selected
    // This prevents canvas movement when interacting with module configurations
    if (selectedModuleId === null) {
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
      setDragStartOffset({ ...panOffset });
    }
    
    // Prevent text selection during drag
    e.preventDefault();
  };

  // Handle module placement start
  const handleModulePlacementStart = (e: React.MouseEvent) => {
    if (!selectedModuleTemplate || !canvasRef.current) return;
    
    const canvasRect = canvasRef.current.getBoundingClientRect();
    const clickX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
    const clickY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
    
    setIsPlacingModule(true);
    
    // Initialize config with default values from template
    const config: Record<string, unknown> = {};
    selectedModuleTemplate.config.forEach(configField => {
      if (configField.defaultValue !== undefined) {
        config[configField.name] = configField.defaultValue;
      }
    });
    
    // Create and place module immediately on click
    const moduleId = `${selectedModuleTemplate.id}_${Date.now()}`;
    const newModule: PlacedModule = {
      id: moduleId,
      template: selectedModuleTemplate,
      position: { x: clickX, y: clickY },
      config,
      nodes: initializeModuleNodes(selectedModuleTemplate, config, moduleId)
    };
    
    setPlacedModules(prev => [...prev, newModule]);
    
    e.preventDefault();
  };

  // Handle mouse move for module placement only (canvas dragging is now global)
  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    // If placing module and dragging, update the most recent module position
    if (isPlacingModule && selectedModuleTemplate && canvasRef.current) {
      const canvasRect = canvasRef.current.getBoundingClientRect();
      const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
      const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
      
      // Update the position of the most recently placed module
      setPlacedModules(prev => {
        if (prev.length === 0) return prev;
        const updatedModules = [...prev];
        updatedModules[updatedModules.length - 1] = {
          ...updatedModules[updatedModules.length - 1],
          position: { x: mouseX, y: mouseY }
        };
        return updatedModules;
      });
    }
  };

  // Handle mouse up - only for module placement, not for dragging (global handlers manage dragging)
  const handleCanvasMouseUp = () => {
    // Only handle module placement cleanup, NOT dragging
    if (isPlacingModule) {
      onModuleSelect(null);
      setIsPlacingModule(false);
    }
    
    // DO NOT stop dragging here - let global handlers manage that
  };

  // Handle mouse leave - only for module placement, not for dragging (global handlers manage dragging)
  const handleCanvasMouseLeave = () => {
    // Only handle module placement cleanup, NOT dragging
    if (isPlacingModule) {
      onModuleSelect(null);
      setIsPlacingModule(false);
    }
    
    // DO NOT stop dragging here - let global handlers manage that
  };


  // Wheel event handler for zoom - runs on every render to ensure canvas is always listening
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      
      // Disable zooming when dragging a module
      if (isDraggingModule) return;
      
      if (!canvasRef.current) return;
      
      const canvasRect = canvasRef.current.getBoundingClientRect();
      const mouseX = e.clientX - canvasRect.left;
      const mouseY = e.clientY - canvasRect.top;
      
      // Calculate new zoom with proper bounds using ref values
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const currentZoom = zoomRef.current;
      const currentPanOffset = panOffsetRef.current;
      
      const newZoom = e.deltaY > 0 
        ? Math.max(currentZoom * zoomFactor, 0.1)  // Zoom out with min limit
        : Math.min(currentZoom * zoomFactor, 3);   // Zoom in with max limit
      
      // Only update if zoom actually changes
      if (newZoom !== currentZoom) {
        // Calculate pan offset to zoom towards mouse position
        const zoomRatio = newZoom / currentZoom;
        const newPanX = mouseX - (mouseX - currentPanOffset.x) * zoomRatio;
        const newPanY = mouseY - (mouseY - currentPanOffset.y) * zoomRatio;
        
        // Apply both updates
        setZoom(newZoom);
        setPanOffset({ x: newPanX, y: newPanY });
      }
    };

    // Always try to attach listener if canvas exists
    const currentCanvas = canvasRef.current;
    if (currentCanvas) {
      // Remove existing listener first to prevent duplicates
      currentCanvas.removeEventListener('wheel', handleWheel);
      // Add the listener
      currentCanvas.addEventListener('wheel', handleWheel, { passive: false });
    }

    return () => {
      if (currentCanvas) {
        currentCanvas.removeEventListener('wheel', handleWheel);
      }
    };
  }); // No dependencies - runs on every render to ensure listener is always active

  // Global mouse handlers for module dragging and canvas dragging
  useEffect(() => {
    const handleGlobalMouseMove = (e: MouseEvent) => {
      // Prevent any other event handlers from interfering
      if (isDragging || isDraggingModule) {
        e.preventDefault();
        e.stopPropagation();
      }

      // Handle module dragging
      if (isDraggingModule && draggedModuleId && canvasRef.current) {
        const canvasRect = canvasRef.current.getBoundingClientRect();
        
        // Calculate new position
        const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
        const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
        
        let newX = mouseX - moduleDragOffset.x;
        let newY = mouseY - moduleDragOffset.y;
        
        // Apply bounds checking - keep modules within reasonable canvas area
        const moduleWidth = 160; // Half of max module width for centering
        const moduleHeight = 50; // Approximate half module height
        const padding = 20; // Minimum distance from edges
        
        // Calculate canvas bounds in world coordinates
        const canvasWidth = canvasRect.width / zoom;
        const canvasHeight = canvasRect.height / zoom;
        const leftBound = (-panOffset.x / zoom) + moduleWidth + padding;
        const rightBound = (-panOffset.x / zoom) + canvasWidth - moduleWidth - padding;
        const topBound = (-panOffset.y / zoom) + moduleHeight + padding;
        const bottomBound = (-panOffset.y / zoom) + canvasHeight - moduleHeight - padding;
        
        // Constrain position within bounds
        newX = Math.max(leftBound, Math.min(rightBound, newX));
        newY = Math.max(topBound, Math.min(bottomBound, newY));
        
        setPlacedModules(prev => 
          prev.map(module => 
            module.id === draggedModuleId 
              ? { ...module, position: { x: newX, y: newY } }
              : module
          )
        );
        return;
      }

      // Handle canvas dragging
      if (isDragging) {
        const deltaX = e.clientX - dragStart.x;
        const deltaY = e.clientY - dragStart.y;
        
        setPanOffset({
          x: dragStartOffset.x + deltaX,
          y: dragStartOffset.y + deltaY,
        });
      }
    };

    const handleGlobalMouseUp = (e: MouseEvent) => {
      if (isDragging || isDraggingModule) {
        e.preventDefault();
        e.stopPropagation();
      }
      if (isDraggingModule) {
        setIsDraggingModule(false);
        setDraggedModuleId(null);
      }
      if (isDragging) {
        setIsDragging(false);
      }
    };

    // Use capture phase to ensure we get events first
    document.addEventListener('mousemove', handleGlobalMouseMove, true);
    document.addEventListener('mouseup', handleGlobalMouseUp, true);
    
    return () => {
      document.removeEventListener('mousemove', handleGlobalMouseMove, true);
      document.removeEventListener('mouseup', handleGlobalMouseUp, true);
    };
  }, [isDraggingModule, draggedModuleId, moduleDragOffset, isDragging, dragStart, dragStartOffset, panOffset, zoom]);

  // Handle pipeline analysis
  const handleAnalyzePipeline = async () => {
    try {
      console.log('Starting step-based pipeline analysis...');
      
      // Separate I/O definers from processing modules
      const processingModules = [];
      const inputDefinitions = [];
      const outputDefinitions = [];
      
      placedModules.forEach(module => {
        if (module.template.category === 'Module Definers') {
          if (module.template.id === 'input_definer') {
            inputDefinitions.push({
              id: module.id,
              name: module.template.name,
              nodes: module.nodes
            });
          } else if (module.template.id === 'output_definer') {
            outputDefinitions.push({
              id: module.id,
              name: module.template.name,
              nodes: module.nodes
            });
          }
        } else {
          processingModules.push({
            id: module.id,
            templateId: module.template.id,
            template: {
              id: module.template.id,
              name: module.template.name,
              description: module.template.description,
              category: module.template.category,
              color: module.template.color
            },
            position: module.position,
            config: module.config,
            nodes: {
              inputs: module.nodes.inputs.map(input => ({
                id: input.id,
                name: input.name,
                type: input.type,
                description: input.description,
                required: input.required
              })),
              outputs: module.nodes.outputs.map(output => ({
                id: output.id,
                name: output.name,
                type: output.type,
                description: output.description,
                required: output.required || false
              }))
            }
          });
        }
      });
      
      // Prepare connections in the new format
      const pipelineConnections = connections.map(conn => ({
        id: conn.id,
        fromModuleId: conn.fromModuleId,
        fromOutputIndex: conn.fromOutputIndex,
        toModuleId: conn.toModuleId,
        toInputIndex: conn.toInputIndex
      }));
      
      console.log(`Separated pipeline: ${processingModules.length} processing modules, ${inputDefinitions.length} inputs, ${outputDefinitions.length} outputs`);
      
      // Call new step-based analyzer
      const result = await analyzePipelineWithSteps(
        processingModules,
        pipelineConnections,
        inputDefinitions,
        outputDefinitions
      );
      
      console.log('Step-based pipeline analysis result:', result);
      
      if (result.success) {
        console.log('\n=== STEP-BASED PIPELINE ANALYSIS ===');
        console.log(`Algorithm: ${result.algorithm}`);
        console.log(`Total Steps: ${result.total_steps}`);
        console.log(`Parallel Opportunities: ${result.parallel_opportunities}`);
        console.log(`Input Definitions: ${result.input_count}`);
        console.log(`Output Definitions: ${result.output_count}`);
        console.log(`Processing Modules: ${result.processing_module_count}`);
        console.log(`Total Entities: ${result.total_entities}`);
        console.log('');
        
        // Display step assignments
        console.log('=== STEP ASSIGNMENTS ===');
        Object.entries(result.step_assignments).forEach(([entityId, step]) => {
          console.log(`Step ${step}: ${entityId}`);
        });
        console.log('');
        
        // Display grouped steps
        console.log('=== EXECUTION STEPS ===');
        Object.entries(result.steps).forEach(([stepNum, entities]) => {
          console.log(`\nStep ${stepNum} (${entities.length} entities${entities.length > 1 ? ' - PARALLEL' : ''}):`);
          entities.forEach(entity => {
            console.log(`  ${entity.type.toUpperCase()}: ${entity.name} (${entity.id})`);
          });
        });
        console.log('\n=== ANALYSIS COMPLETE ===');
      } else {
        console.error('Step-based pipeline analysis failed');
      }

      
    } catch (error) {
      console.error('Error analyzing pipeline:', error);
      // Show error to user (you could add a toast notification here)
      alert(`Error analyzing pipeline: ${error.message}`);
    }
  };

  // Handle execute pipeline - with input collection modal
  const handleExecutePipeline = async () => {
    try {
      console.log('Starting step-based pipeline execution...');
      
      // Step 1: Prepare pipeline data (same as analyze)
      const processingModules = [];
      const inputDefinitions = [];
      const outputDefinitions = [];
      
      placedModules.forEach(module => {
        if (module.template.category === 'Module Definers') {
          if (module.template.id === 'input_definer') {
            inputDefinitions.push({
              id: module.id,
              name: module.template.name,
              nodes: module.nodes
            });
          } else if (module.template.id === 'output_definer') {
            outputDefinitions.push({
              id: module.id,
              name: module.template.name,
              nodes: module.nodes
            });
          }
        } else {
          processingModules.push({
            id: module.id,
            templateId: module.template.id,
            config: module.config,
            position: module.position,
            nodes: module.nodes
          });
        }
      });
      
      const pipelineConnections = connections.map(conn => ({
        id: conn.id,
        fromModuleId: conn.fromModuleId,
        fromOutputIndex: conn.fromOutputIndex,
        toModuleId: conn.toModuleId,
        toInputIndex: conn.toInputIndex
      }));

      // Step 2: Check if we have input definitions
      if (inputDefinitions.length === 0) {
        alert('No input definitions found. Please add input definers to your pipeline.');
        return;
      }

      // Step 3: Store execution data and open input collection modal
      setCurrentExecutionData({
        processingModules,
        inputDefinitions,
        outputDefinitions,
        pipelineConnections
      });
      setIsInputModalOpen(true);
      
    } catch (error) {
      console.error('Error executing pipeline:', error);
      alert(`Error executing pipeline: ${error.message}`);
    }
  };

  // Handle modal submission - execute pipeline with collected input data
  const handleInputModalSubmit = async (inputData: Record<string, any>) => {
    try {
      if (!currentExecutionData) {
        console.error('No execution data available');
        return;
      }

      setIsInputModalOpen(false);
      console.log('Input data collected:', inputData);

      // Execute pipeline with collected data
      const { executePipelineWithSteps } = await import('../../services/transformationPipelineApi');
      
      const result = await executePipelineWithSteps(
        currentExecutionData.processingModules,
        currentExecutionData.pipelineConnections,
        currentExecutionData.inputDefinitions,
        currentExecutionData.outputDefinitions,
        inputData
      );
      
      console.log('Pipeline execution result:', result);
      
      if (result.success) {
        console.log('\n=== PIPELINE EXECUTION SUCCESSFUL ===');
        console.log('Analysis:', result.analysis);
        console.log('Final outputs:', result.outputs);
        console.log('=== EXECUTION COMPLETE ===');
        
        // Show success to user
        alert(`Pipeline executed successfully! Final outputs: ${JSON.stringify(result.outputs, null, 2)}`);
      } else {
        console.error('Pipeline execution failed');
        alert('Pipeline execution failed. Check console for details.');
      }
      
    } catch (error) {
      console.error('Error executing pipeline:', error);
      alert(`Error executing pipeline: ${error.message}`);
    } finally {
      // Clean up execution data
      setCurrentExecutionData(null);
    }
  };

  // Handle modal cancellation
  const handleInputModalCancel = () => {
    setIsInputModalOpen(false);
    setCurrentExecutionData(null);
  };

  // Handle print objects (debug function)
  const handlePrintObjects = () => {
    console.log('=== PIPELINE OBJECTS DEBUG ===');
    
    // Prepare the same pipeline data that would be sent to backend
    const pipelineData = {
      modules: placedModules.map(module => ({
        id: module.id,
        templateId: module.template.id,
        template: {
          id: module.template.id,
          name: module.template.name,
          description: module.template.description,
          category: module.template.category,
          color: module.template.color
        },
        position: module.position,
        config: module.config,
        nodes: {
          inputs: module.nodes.inputs.map(input => ({
            id: input.id,
            name: input.name,
            type: input.type,
            description: input.description,
            required: input.required
          })),
          outputs: module.nodes.outputs.map(output => ({
            id: output.id,
            name: output.name,
            type: output.type,
            description: output.description,
            required: output.required || false
          }))
        }
      })),
      connections: connections.map(conn => ({
        id: conn.id,
        from: {
          moduleId: conn.fromModuleId,
          outputIndex: conn.fromOutputIndex
        },
        to: {
          moduleId: conn.toModuleId,
          inputIndex: conn.toInputIndex
        }
      }))
    };
    
    console.log('Pipeline Data Structure:');
    console.log(JSON.stringify(pipelineData, null, 2));
    
    console.log('\n=== MODULES ===');
    pipelineData.modules.forEach(module => {
      console.log(`Module: ${module.template.name} (${module.id})`);
      console.log(`  Template ID: ${module.templateId}`);
      console.log(`  Category: ${module.template.category}`);
      console.log(`  Position: (${module.position.x}, ${module.position.y})`);
      console.log(`  Config:`, module.config);
      console.log(`  Inputs: ${module.nodes.inputs.length}`);
      module.nodes.inputs.forEach((input, idx) => {
        console.log(`    ${idx}: ${input.name} (${input.type}) - ${input.description}`);
      });
      console.log(`  Outputs: ${module.nodes.outputs.length}`);
      module.nodes.outputs.forEach((output, idx) => {
        console.log(`    ${idx}: ${output.name} (${output.type}) - ${output.description}`);
      });
      console.log('');
    });
    
    console.log('=== CONNECTIONS ===');
    pipelineData.connections.forEach(conn => {
      const fromModule = pipelineData.modules.find(m => m.id === conn.from.moduleId);
      const toModule = pipelineData.modules.find(m => m.id === conn.to.moduleId);
      const fromOutput = fromModule?.nodes.outputs[conn.from.outputIndex];
      const toInput = toModule?.nodes.inputs[conn.to.inputIndex];
      
      console.log(`Connection ${conn.id}:`);
      console.log(`  From: ${fromModule?.template.name}[${fromOutput?.name}] (index ${conn.from.outputIndex})`);
      console.log(`  To: ${toModule?.template.name}[${toInput?.name}] (index ${conn.to.inputIndex})`);
      console.log(`  Type: ${fromOutput?.type} -> ${toInput?.type}`);
      console.log('');
    });
    
    console.log(`Total Modules: ${pipelineData.modules.length}`);
    console.log(`Total Connections: ${pipelineData.connections.length}`);
    console.log('=== END DEBUG ===');
  };

  // Handle get base modules (debug function)
  const handleGetBaseModules = async () => {
    try {
      console.log('=== BASE MODULES FROM DATABASE ===');
      console.log('Fetching base modules from transformation pipeline database...');
      
      const result = await apiClient.getBaseModules();
      
      if (result.success) {
        console.log('\n=== DATABASE MODULES ===');
        console.log(`Total modules in database: ${result.modules.length}`);
        console.log('');
        
        // Group by category for better organization
        const modulesByCategory = result.modules.reduce((acc, module) => {
          const category = module.category || 'Uncategorized';
          if (!acc[category]) {
            acc[category] = [];
          }
          acc[category].push(module);
          return acc;
        }, {} as Record<string, typeof result.modules>);
        
        Object.entries(modulesByCategory).forEach(([category, modules]) => {
          console.log(`\n📁 CATEGORY: ${category.toUpperCase()}`);
          console.log(`   Modules: ${modules.length}`);
          console.log('   ' + '─'.repeat(50));
          
          modules.forEach(module => {
            console.log(`\n   🔧 ${module.name} (${module.id})`);
            console.log(`      📝 Description: ${module.description || 'No description'}`);
            console.log(`      🏷️ Version: ${module.version}`);
            console.log(`      🎨 Color: ${module.color}`);
            console.log(`      📥 Inputs: ${module.inputs.length}`);
            module.inputs.forEach((input, idx) => {
              const required = input.required ? ' (required)' : '';
              console.log(`         ${idx + 1}. ${input.name} (${input.type})${required} - ${input.description}`);
            });
            console.log(`      📤 Outputs: ${module.outputs.length}`);
            module.outputs.forEach((output, idx) => {
              const required = output.required ? ' (required)' : '';
              console.log(`         ${idx + 1}. ${output.name} (${output.type})${required} - ${output.description}`);
            });
            console.log(`      ⚙️ Configuration: ${module.config.length} options`);
            module.config.forEach((config, idx) => {
              const required = config.required ? ' (required)' : '';
              const defaultVal = config.defaultValue !== undefined ? ` [default: ${JSON.stringify(config.defaultValue)}]` : '';
              console.log(`         ${idx + 1}. ${config.name} (${config.type})${required}${defaultVal} - ${config.description}`);
            });
            
            // Show dynamic configuration if available
            if (module.maxInputs !== undefined) {
              console.log(`      🔗 Max Inputs: ${module.maxInputs || 'unlimited'}`);
            }
            if (module.maxOutputs !== undefined) {
              console.log(`      🔗 Max Outputs: ${module.maxOutputs || 'unlimited'}`);
            }
            if (module.dynamicInputs) {
              console.log(`      🔄 Dynamic Inputs: ${JSON.stringify(module.dynamicInputs)}`);
            }
            if (module.dynamicOutputs) {
              console.log(`      🔄 Dynamic Outputs: ${JSON.stringify(module.dynamicOutputs)}`);
            }
          });
        });
        
        console.log('\n=== SUMMARY ===');
        console.log(`Categories: ${Object.keys(modulesByCategory).length}`);
        Object.entries(modulesByCategory).forEach(([category, modules]) => {
          console.log(`  ${category}: ${modules.length} modules`);
        });
        
        console.log('\n=== FULL JSON DATA ===');
        console.log(JSON.stringify(result, null, 2));
        
      } else {
        console.error('Failed to fetch base modules:', result.message);
      }
      
      console.log('=== END BASE MODULES DEBUG ===');
      
    } catch (error) {
      console.error('Error fetching base modules:', error);
      console.error('Make sure the unified ETO server is running on port 8080');
    }
  };

  // Handle module deletion
  const handleModuleDelete = (moduleId: string) => () => {
    setPlacedModules(prev => prev.filter(module => module.id !== moduleId));
    
    // Clear selection if deleted module was selected
    if (selectedModuleId === moduleId) {
      setSelectedModuleId(null);
    }
    
    // Remove all node positions for this module
    setNodePositions(prev => {
      const newPositions = { ...prev };
      Object.keys(newPositions).forEach(key => {
        if (key.startsWith(`${moduleId}-`)) {
          delete newPositions[key];
        }
      });
      return newPositions;
    });
    
    // Remove all connections associated with this module
    setConnections(prev => {
      const connectionsToRemove = prev.filter(connection => 
        connection.fromModuleId === moduleId || connection.toModuleId === moduleId
      );
      
      // Clear selection if selected connection is being deleted
      connectionsToRemove.forEach(connection => {
        if (selectedConnectionId === connection.id) {
          setSelectedConnectionId(null);
        }
      });
      
      return prev.filter(connection => 
        connection.fromModuleId !== moduleId && connection.toModuleId !== moduleId
      );
    });
    
    // Cancel any starting connection from this module
    if (startingConnection && startingConnection.moduleId === moduleId) {
      setStartingConnection(null);
    }
  };

  // Handle module config change
  const handleModuleConfigChange = (moduleId: string) => (config: Record<string, unknown>) => {
    setPlacedModules(prev => 
      prev.map(module => {
        if (module.id === moduleId) {
          const updatedModule = { ...module, config };
          
          // For input/output definers, sync node type with data_type config
          if (module.template.category === 'Module Definers' && config.data_type) {
            const newType = config.data_type as 'string' | 'number' | 'boolean' | 'datetime';
            
            // Update the single node's type
            if (module.nodes.inputs.length > 0) {
              // Output definer (has input)
              updatedModule.nodes = {
                ...module.nodes,
                inputs: module.nodes.inputs.map(node => ({ ...node, type: newType }))
              };
            } else if (module.nodes.outputs.length > 0) {
              // Input definer (has output) 
              updatedModule.nodes = {
                ...module.nodes,
                outputs: module.nodes.outputs.map(node => ({ ...node, type: newType }))
              };
            }
          }
          
          // If module has generateNodes, update node state
          if (module.template.generateNodes) {
            const generated = module.template.generateNodes(config);
            updatedModule.nodes = {
              inputs: generated.inputs.map((input, index) => ({
                id: `${module.id}_input_${index}`,
                name: input.name || `Input ${index + 1}`,
                type: input.type,
                description: input.description,
                required: input.required
              })),
              outputs: generated.outputs.map((output, index) => ({
                id: `${module.id}_output_${index}`,
                name: output.name || `Output ${index + 1}`,
                type: output.type,
                description: output.description,
                required: output.required || false
              }))
            };
          }
          
          return updatedModule;
        }
        return module;
      })
    );
  };

  // Handle module mouse down (start dragging)
  const handleModuleMouseDown = (moduleId: string) => (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left mouse button
    
    e.preventDefault(); // Prevent text selection
    e.stopPropagation();
    
    const module = placedModules.find(m => m.id === moduleId);
    if (!module || !canvasRef.current) return;
    
    const canvasRect = canvasRef.current.getBoundingClientRect();
    
    // Calculate offset from mouse to module center
    const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
    const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
    
    const offsetX = mouseX - module.position.x;
    const offsetY = mouseY - module.position.y;
    
    setIsDraggingModule(true);
    setDraggedModuleId(moduleId);
    setModuleDragOffset({ x: offsetX, y: offsetY });
  };

  // Get node position directly from DOM elements (real-time)
  const getNodePosition = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number): { x: number; y: number } => {
    // Try to find the actual DOM element for this node
    const nodeSelector = `[data-node-id="${moduleId}-${nodeType}-${nodeIndex}"]`;
    const nodeElement = document.querySelector(nodeSelector);
    
    if (nodeElement && canvasRef.current) {
      const nodeRect = nodeElement.getBoundingClientRect();
      const canvasRect = canvasRef.current.getBoundingClientRect();
      
      // Calculate center of the node element
      const centerX = nodeRect.left + nodeRect.width / 2;
      const centerY = nodeRect.top + nodeRect.height / 2;
      
      // Convert from screen coordinates to canvas coordinates
      const canvasX = (centerX - canvasRect.left - panOffset.x) / zoom;
      const canvasY = (centerY - canvasRect.top - panOffset.y) / zoom;
      
      return { x: canvasX, y: canvasY };
    }
    
    // Fallback to cached position if DOM element not found
    const nodeKey = `${moduleId}-${nodeType}-${nodeIndex}`;
    const cachedPosition = nodePositions[nodeKey];
    
    if (cachedPosition && canvasRef.current) {
      const canvasRect = canvasRef.current.getBoundingClientRect();
      const canvasX = (cachedPosition.x - canvasRect.left - panOffset.x) / zoom;
      const canvasY = (cachedPosition.y - canvasRect.top - panOffset.y) / zoom;
      return { x: canvasX, y: canvasY };
    }
    
    // Final fallback to module center
    const module = placedModules.find(m => m.id === moduleId);
    return module ? module.position : { x: 0, y: 0 };
  };

  // Handle node click (start or complete connection)
  const handleNodeClick = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    
    // Clear any selected connection when interacting with nodes
    if (selectedConnectionId) {
      setSelectedConnectionId(null);
    }
    
    if (!startingConnection) {
      // Start new connection
      console.log(`Starting connection from ${moduleId}[${nodeType}${nodeIndex}]`);
      setStartingConnection({ moduleId, type: nodeType, index: nodeIndex });
      // Initialize mouse position to the starting node position
      const startPos = getNodePosition(moduleId, nodeType, nodeIndex);
      setCurrentMousePosition(startPos);
    } else {
      // Try to complete connection
      console.log(`Trying to complete connection from ${startingConnection.moduleId}[${startingConnection.type}${startingConnection.index}] to ${moduleId}[${nodeType}${nodeIndex}]`);
      const start = startingConnection;
      
      // Can only connect output to input or input to output, and not to same module
      if (start.type !== nodeType && start.moduleId !== moduleId) {
        console.log(`Connection validation passed: ${start.type} -> ${nodeType}, different modules`);
        // Get types of both nodes for validation
        const startNodeType = getNodeType(start.moduleId, start.type, start.index);
        const endNodeType = getNodeType(moduleId, nodeType, nodeIndex);
        
        // Allow connections between nodes of the same type, or if either node is an I/O definer
        const startModule = placedModules.find(m => m.id === start.moduleId);
        const endModule = placedModules.find(m => m.id === moduleId);
        const isStartIODefiner = startModule?.template.category === 'Module Definers';
        const isEndIODefiner = endModule?.template.category === 'Module Definers';
        
        
        // Check if connection should be allowed
        let connectionAllowed = false;
        let reason = "";
        
        // Allow if types already match
        if (startNodeType === endNodeType) {
          connectionAllowed = true;
          reason = "types match";
        }
        // Allow if either node has undefined type (I/O definers start undefined)
        else if (startNodeType === 'undefined' || endNodeType === 'undefined') {
          connectionAllowed = true;
          reason = "undefined type can connect to any type";
        }
        // Allow if either is an I/O definer (existing logic)
        else if (isStartIODefiner || isEndIODefiner) {
          connectionAllowed = true;
          reason = "I/O definer present";
        }
        // NEW: Allow if target node can change to match source type
        else if (getNodeTypeConfigAllowed(moduleId, nodeType)) {
          const targetAllowedTypes = nodeType === 'input' 
            ? endModule?.template.inputAllowedTypes || []
            : endModule?.template.outputAllowedTypes || [];
          const canTargetAcceptSourceType = targetAllowedTypes.length === 0 || targetAllowedTypes.includes(startNodeType);
          
          if (canTargetAcceptSourceType) {
            connectionAllowed = true;
            reason = "target can change to match source";
          }
        }
        // NEW: Allow if source node can change to match target type
        else if (getNodeTypeConfigAllowed(start.moduleId, start.type)) {
          const sourceAllowedTypes = start.type === 'input' 
            ? startModule?.template.inputAllowedTypes || []
            : startModule?.template.outputAllowedTypes || [];
          const canSourceAcceptTargetType = sourceAllowedTypes.length === 0 || sourceAllowedTypes.includes(endNodeType);
          
          if (canSourceAcceptTargetType) {
            connectionAllowed = true;
            reason = "source can change to match target";
          }
        }
        
        console.log(`Connection decision: ${connectionAllowed ? 'ALLOWED' : 'REJECTED'} - ${reason}`);
        
        if (connectionAllowed) {
          const newConnection: NodeConnection = {
            id: `${Date.now()}`,
            fromModuleId: start.type === 'output' ? start.moduleId : moduleId,
            fromOutputIndex: start.type === 'output' ? start.index : nodeIndex,
            toModuleId: start.type === 'input' ? start.moduleId : moduleId,
            toInputIndex: start.type === 'input' ? start.index : nodeIndex,
          };
          
          // Check if connection already exists
          const connectionExists = connections.some(conn => 
            conn.fromModuleId === newConnection.fromModuleId &&
            conn.fromOutputIndex === newConnection.fromOutputIndex &&
            conn.toModuleId === newConnection.toModuleId &&
            conn.toInputIndex === newConnection.toInputIndex
          );
          
          if (!connectionExists) {
            // Check if the input already has a connection (inputs can only have one connection)
            const existingInputConnection = connections.find(conn => 
              conn.toModuleId === newConnection.toModuleId &&
              conn.toInputIndex === newConnection.toInputIndex
            );
            
            // BEFORE adding connection: Automatic type matching
            const sourceType = getNodeType(start.moduleId, start.type, start.index);
            const targetType = getNodeType(moduleId, nodeType, nodeIndex);
            
            
            // Auto-match types if they're different
            if (sourceType !== targetType) {
              
              // Get type flexibility for both nodes
              const sourceCanChange = getNodeTypeConfigAllowed(start.moduleId, start.type);
              const targetCanChange = getNodeTypeConfigAllowed(moduleId, nodeType);
              
              const sourceAllowedTypes = start.type === 'input' 
                ? startModule?.template.inputAllowedTypes || []
                : startModule?.template.outputAllowedTypes || [];
              const targetAllowedTypes = nodeType === 'input' 
                ? endModule?.template.inputAllowedTypes || []
                : endModule?.template.outputAllowedTypes || [];
              
              const sourceIsRestricted = sourceAllowedTypes.length > 0; // Has specific allowed types
              const targetIsRestricted = targetAllowedTypes.length > 0; // Has specific allowed types
              
              
              let changeSource = false;
              let changeTarget = false;
              let newSourceType = sourceType;
              let newTargetType = targetType;
              
              // Check if either node is an I/O definer
              const sourceIsIODefiner = startModule?.template.category === 'Module Definers';
              const targetIsIODefiner = endModule?.template.category === 'Module Definers';
              
              // Special rule for undefined types: they always change to match the defined type
              if (sourceType === 'undefined' && targetType !== 'undefined') {
                changeSource = true;
                newSourceType = targetType;
              }
              else if (targetType === 'undefined' && sourceType !== 'undefined') {
                changeTarget = true;
                newTargetType = sourceType;
              }
              // Special rule for I/O definers: they always change to match the other module (unless undefined rule already applies)
              else if (sourceIsIODefiner && !targetIsIODefiner) {
                changeSource = true;
                newSourceType = targetType;
              }
              else if (targetIsIODefiner && !sourceIsIODefiner) {
                changeTarget = true;
                newTargetType = sourceType;
              }
              // If both are I/O definers, use the default behavior
              else if (!sourceIsIODefiner && !targetIsIODefiner) {
                // Rule 1: If one node has restricted types and the other can change types → dynamic node switches
                if (sourceIsRestricted && !targetIsRestricted && targetCanChange && targetAllowedTypes.includes(sourceType)) {
                  changeTarget = true;
                  newTargetType = sourceType;
                }
                else if (targetIsRestricted && !sourceIsRestricted && sourceCanChange && sourceAllowedTypes.includes(targetType)) {
                  changeSource = true;
                  newSourceType = targetType;
                }
                // Rule 2: In any other scenario → target node switches to match source
                else if (targetCanChange && (targetAllowedTypes.length === 0 || targetAllowedTypes.includes(sourceType))) {
                  changeTarget = true;
                  newTargetType = sourceType;
                }
                // Fallback: If target can't change but source can
                else if (sourceCanChange && (sourceAllowedTypes.length === 0 || sourceAllowedTypes.includes(targetType))) {
                  changeSource = true;
                  newSourceType = targetType;
                }
              }
              
              // Apply the type changes
              if (changeSource || changeTarget) {
                setPlacedModules(prevModules => {
                  return prevModules.map(module => {
                    // Change source node type
                    if (changeSource && module.id === start.moduleId) {
                      const nodeToUpdate = start.type === 'input'
                        ? { inputs: module.nodes.inputs.map((node, idx) => 
                            idx === start.index ? { ...node, type: newSourceType } : node
                          ), outputs: module.nodes.outputs }
                        : { inputs: module.nodes.inputs, outputs: module.nodes.outputs.map((node, idx) => 
                            idx === start.index ? { ...node, type: newSourceType } : node
                          ) };
                      return { ...module, nodes: nodeToUpdate };
                    }
                    
                    // Change target node type
                    if (changeTarget && module.id === moduleId) {
                      const nodeToUpdate = nodeType === 'input'
                        ? { inputs: module.nodes.inputs.map((node, idx) => 
                            idx === nodeIndex ? { ...node, type: newTargetType } : node
                          ), outputs: module.nodes.outputs }
                        : { inputs: module.nodes.inputs, outputs: module.nodes.outputs.map((node, idx) => 
                            idx === nodeIndex ? { ...node, type: newTargetType } : node
                          ) };
                      return { ...module, nodes: nodeToUpdate };
                    }
                    
                    return module;
                  });
                });
              } else {
                console.log(`No type changes applied - no compatible match found`);
              }
            } else {
              console.log(`Types already match - no auto-matching needed`);
            }

            setConnections(prev => {
              let updatedConnections = [...prev];
              
              // Remove existing connection to this input if it exists
              if (existingInputConnection) {
                updatedConnections = updatedConnections.filter(conn => conn.id !== existingInputConnection.id);
                
                // Clear selection if we're replacing the selected connection
                if (selectedConnectionId === existingInputConnection.id) {
                  setSelectedConnectionId(null);
                }
              }
              
              // Add the new connection
              return [...updatedConnections, newConnection];
            });
          }
        }
      }
      
      // Clear starting connection
      setStartingConnection(null);
    }
  };

  // Generate bezier path for connection - direction aware
  const generateBezierPath = (start: { x: number; y: number }, end: { x: number; y: number }, startType?: 'input' | 'output'): string => {
    const controlPointOffset = Math.abs(end.x - start.x) * 0.5;
    
    let cp1x, cp2x;
    
    if (startType === 'input') {
      // Starting from input node (left side) - curve should go left then right
      cp1x = start.x - controlPointOffset;
      cp2x = end.x + controlPointOffset;
    } else {
      // Starting from output node (right side) or standard connection - curve should go right then left
      cp1x = start.x + controlPointOffset;
      cp2x = end.x - controlPointOffset;
    }
    
    const cp1y = start.y;
    const cp2y = end.y;
    
    return `M ${start.x} ${start.y} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${end.x} ${end.y}`;
  };

  // Handle drag over canvas
  const handleCanvasDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  // Handle drop on canvas
  const handleCanvasDrop = (e: React.DragEvent) => {
    e.preventDefault();
    
    if (!canvasRef.current) return;
    
    try {
      // Try to get data from different sources (for custom module builder compatibility)
      let data: any;
      try {
        data = JSON.parse(e.dataTransfer.getData('application/json'));
      } catch {
        data = JSON.parse(e.dataTransfer.getData('text/plain'));
      }
      
      const canvasRect = canvasRef.current.getBoundingClientRect();
      
      // Calculate drop position relative to canvas, accounting for zoom and pan
      const dropX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
      const dropY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
      
      // Handle Input/Output Definers as regular modules (only for custom module builder)
      if (enableInputOutputDefiners && (data.type === 'input_definer' || data.type === 'output_definer')) {
        // Transform definer data into module template format
        const moduleTemplate: BaseModuleTemplate = {
          id: data.id,
          name: data.name,
          description: data.type === 'input_definer' ? 'Define an input for your custom module' : 'Define an output for your custom module',
          category: 'Module Definers',
          color: data.type === 'input_definer' ? '#FFFFFF' : '#000000',
          inputs: data.type === 'input_definer' ? [] : [{ name: 'Value', type: 'undefined', description: 'Input value', required: true }],
          outputs: data.type === 'input_definer' ? [{ name: 'Value', type: 'undefined', description: 'Output value', required: true }] : [],
          config: [] // No config needed - field name and type are handled inline
        };
        
        // Process as regular module
        data = moduleTemplate;
      }
      
      // Handle regular module placement
      const moduleData = data as BaseModuleTemplate;
      
      // Initialize config with default values from template
      const config: Record<string, unknown> = {};
      moduleData.config?.forEach(configField => {
        if (configField.defaultValue !== undefined) {
          config[configField.name] = configField.defaultValue;
        }
      });
      
      // Create new placed module
      const moduleId = `${moduleData.id}_${Date.now()}`;
      const newModule: PlacedModule = {
        id: moduleId,
        template: moduleData,
        position: { x: dropX, y: dropY },
        config,
        nodes: initializeModuleNodes(moduleData, config, moduleId)
      };
      
      setPlacedModules(prev => [...prev, newModule]);
      
      // Clear selection after successful drop
      onModuleSelect(null);
      
    } catch (error) {
      console.error('Failed to parse dropped data:', error);
    }
  };
  
  return (
    <div className="flex-1 relative">
      {/* Canvas with layered architecture */}
      <GraphCanvas
        zoom={zoom}
        panOffset={panOffset}
        isDragging={isDragging}
        onMouseDown={handleCanvasMouseDown}
        onMouseMove={handleCanvasMouseMove}
        onMouseUp={handleCanvasMouseUp}
        onMouseLeave={handleCanvasMouseLeave}
        onDragOver={handleCanvasDragOver}
        onDrop={handleCanvasDrop}
        canvasRef={canvasRef}
      >
        {/* Connection Layer - Behind modules */}
        <ConnectionLayer
          connections={connections}
          selectedConnectionId={selectedConnectionId}
          startingConnection={startingConnection}
          currentMousePosition={currentMousePosition}
          getNodePosition={getNodePosition}
          getNodeType={getNodeType}
          getTypeColor={getTypeColor}
          generateBezierPath={generateBezierPath}
          onConnectionClick={handleConnectionClick}
        />

        {/* Module Layer - In front of connections */}
        <ModuleLayer
          placedModules={placedModules}
          connections={connections}
          zoom={zoom}
          panOffset={panOffset}
          onModuleMouseDown={handleModuleMouseDown}
          onModuleDelete={handleModuleDelete}
          onModuleConfigChange={handleModuleConfigChange}
          onNodeClick={handleNodeClick}
          onNodePositionUpdate={handleNodePositionUpdate}
          onAddInput={handleAddInput}
          onRemoveInput={handleRemoveInput}
          onAddOutput={handleAddOutput}
          onRemoveOutput={handleRemoveOutput}
          onNodeTypeChange={handleNodeTypeChange}
          onNodeNameChange={handleNodeNameChange}
          getInputDisplayName={getInputDisplayName}
          canChangeType={canNodeChangeType}
        />

      </GraphCanvas>

      {/* Overlay Components - Above everything */}
      <GraphOverlays
        connections={connections}
        selectedConnectionId={selectedConnectionId}
        startingConnection={startingConnection}
        placedModules={placedModules}
        zoom={zoom}
        isDraggingModule={isDraggingModule}
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onResetZoom={resetZoom}
        onConnectionDelete={handleConnectionDelete}
        onAnalyzePipeline={handleAnalyzePipeline}
        onExecutePipeline={handleExecutePipeline}
        onPrintObjects={handlePrintObjects}
        onGetBaseModules={handleGetBaseModules}
        getTypeColor={getTypeColor}
      />

      {/* Input Collection Modal */}
      <InputCollectionModal
        isOpen={isInputModalOpen}
        inputDefinitions={currentExecutionData?.inputDefinitions || []}
        onSubmit={handleInputModalSubmit}
        onCancel={handleInputModalCancel}
      />
    </div>
  );
};