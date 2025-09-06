import React, { useState, useRef, useEffect, useCallback } from 'react';
import { BaseModuleTemplate } from '../../types/modules';
import { mockExtractedFields } from '../../data/testModules';
import { InputDefiner, OutputDefiner } from '../../types/inputOutputDefiners';
import { GraphCanvas } from './canvas/GraphCanvas';
import { ModuleLayer } from './layers/ModuleLayer';
import { ConnectionLayer } from './layers/ConnectionLayer';
import { GraphOverlays } from './overlays/GraphOverlays';
import { InputOutputDefinerComponent } from './module-builder/InputOutputDefinerComponent';

// Types (extracted from original file)
interface NodeState {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime' | 'variant';
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
      case 'variant': return '#6B7280'; // Gray (accepts any type)
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
  const initializeModuleNodes = (template: BaseModuleTemplate, config: Record<string, unknown>): ModuleNodeState => {
    let inputs: NodeState[] = [];
    let outputs: NodeState[] = [];
    
    // Use generateNodes if available for dynamic modules
    if (template.generateNodes) {
      const generated = template.generateNodes(config);
      inputs = generated.inputs.map((input, index) => ({
        id: `${template.id}_input_${index}`,
        name: input.name || `Input ${index + 1}`,
        type: input.type,
        description: input.description,
        required: input.required
      }));
      outputs = generated.outputs.map((output, index) => ({
        id: `${template.id}_output_${index}`,
        name: output.name || `Output ${index + 1}`,
        type: output.type,
        description: output.description,
        required: output.required || false
      }));
    } else {
      // Use template nodes for static modules
      inputs = template.inputs.map((input, index) => ({
        id: `${template.id}_input_${index}`,
        name: input.name || `Input ${index + 1}`,
        type: input.type,
        description: input.description,
        required: input.required
      }));
      outputs = template.outputs.map((output, index) => ({
        id: `${template.id}_output_${index}`,
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
      return module.template.dynamicInputs?.allowTypeConfiguration || false;
    } else {
      return module.template.dynamicOutputs?.allowTypeConfiguration || false;
    }
  };

  // Helper function to check if a node can change type based on connections
  const canNodeChangeType = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number): boolean => {
    // First check if this node itself allows type configuration
    if (!getNodeTypeConfigAllowed(moduleId, nodeType)) {
      return false;
    }

    if (nodeType === 'input') {
      // Check if input is connected
      const connection = connections.find(conn => 
        conn.toModuleId === moduleId && conn.toInputIndex === nodeIndex
      );
      
      if (!connection) {
        return true; // No connection, can change type
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
      
      // All connected inputs must allow type configuration
      return outputConnections.every(connection => 
        getNodeTypeConfigAllowed(connection.toModuleId, 'input')
      );
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
  const handleNodeTypeChange = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: 'string' | 'number' | 'boolean' | 'datetime' | 'variant') => {
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

      // Synchronize connected nodes if they allow type configuration
      if (nodeType === 'input') {
        // Find connected output and update its type if it allows configuration
        const connection = connections.find(conn => 
          conn.toModuleId === moduleId && conn.toInputIndex === nodeIndex
        );
        
        if (connection && getNodeTypeConfigAllowed(connection.fromModuleId, 'output')) {
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
      } else {
        // Find all connected inputs and update their types if they allow configuration
        const outputConnections = connections.filter(conn => 
          conn.fromModuleId === moduleId && conn.fromOutputIndex === nodeIndex
        );
        
        outputConnections.forEach(connection => {
          if (getNodeTypeConfigAllowed(connection.toModuleId, 'input')) {
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

  // Handle node name changes for outputs
  const handleNodeNameChange = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => {
    // Only allow name changes for outputs
    if (nodeType !== 'output') return;
    
    setPlacedModules(prev => prev.map(module => {
      if (module.id !== moduleId) return module;
      
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
    const newModule: PlacedModule = {
      id: `${selectedModuleTemplate.id}_${Date.now()}`,
      template: selectedModuleTemplate,
      position: { x: clickX, y: clickY },
      config,
      nodes: initializeModuleNodes(selectedModuleTemplate, config)
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
            const newType = config.data_type as 'string' | 'number' | 'boolean' | 'datetime' | 'variant';
            
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
      setStartingConnection({ moduleId, type: nodeType, index: nodeIndex });
      // Initialize mouse position to the starting node position
      const startPos = getNodePosition(moduleId, nodeType, nodeIndex);
      setCurrentMousePosition(startPos);
    } else {
      // Try to complete connection
      const start = startingConnection;
      
      // Can only connect output to input or input to output, and not to same module
      if (start.type !== nodeType && start.moduleId !== moduleId) {
        // Get types of both nodes for validation
        const startNodeType = getNodeType(start.moduleId, start.type, start.index);
        const endNodeType = getNodeType(moduleId, nodeType, nodeIndex);
        
        // Only allow connections between nodes of the same type
        if (startNodeType === endNodeType) {
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
          inputs: data.type === 'input_definer' ? [] : [{ name: 'Value', type: 'variant', description: 'Input value', required: true }],
          outputs: data.type === 'input_definer' ? [{ name: 'Value', type: 'variant', description: 'Output value', required: true }] : [],
          config: [
            {
              name: 'field_name',
              type: 'text',
              description: 'Field Name',
              required: true,
              defaultValue: data.type === 'input_definer' ? 'input_name' : 'output_name',
              placeholder: 'Enter field name'
            },
            {
              name: 'data_type',
              type: 'select',
              description: 'Data Type',
              required: true,
              defaultValue: 'string',
              options: ['string', 'number', 'boolean', 'datetime', 'variant']
            }
          ]
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
      const newModule: PlacedModule = {
        id: `${moduleData.id}_${Date.now()}`,
        template: moduleData,
        position: { x: dropX, y: dropY },
        config,
        nodes: initializeModuleNodes(moduleData, config)
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
        getTypeColor={getTypeColor}
      />
    </div>
  );
};