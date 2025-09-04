import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef, useEffect, useCallback } from "react";
import { ModuleSelectionPane } from "../../components/ModuleSelectionPane";
import { GraphModuleComponent } from "../../components/GraphModuleComponent";
import { ExtractedDataModuleComponent } from "../../components/ExtractedDataModuleComponent";
import { NewGraphModuleComponent } from "../../components/NewGraphModuleComponent";
import { testBaseModules, BaseModuleTemplate, ModuleInput, ModuleOutput } from "../../data/testModules";

export const Route = createFileRoute("/transformation_pipeline/graph")({
  component: TransformationPipelineGraph,
});

interface NodeState {
  id: string;
  name?: string; // Optional for inputs (computed from connections), required for outputs
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
  config: any;
  
  // Node state (replaces runtime inputs/outputs)
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

function TransformationPipelineGraph() {
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  
  // Refs to access current zoom and pan values without causing useEffect re-creation
  const zoomRef = useRef(zoom);
  const panOffsetRef = useRef(panOffset);
  
  // Keep refs in sync with state
  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);
  
  useEffect(() => {
    panOffsetRef.current = panOffset;
  }, [panOffset]);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [dragStartOffset, setDragStartOffset] = useState({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLDivElement>(null);

  // Module selection and placement state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [selectedModuleTemplate, setSelectedModuleTemplate] = useState<BaseModuleTemplate | null>(null);
  const [placedModules, setPlacedModules] = useState<PlacedModule[]>([]);

  // Auto-place extracted data modules and Type Coercion module on initial load
  useEffect(() => {
    if (placedModules.length === 0) {
      const extractedDataModules = testBaseModules.filter(module => module.category === 'Extracted Data');
      const typeCoercionModule = testBaseModules.find(module => module.id === 'type_coercion');
      const dataCombinerModule = testBaseModules.find(module => module.id === 'data_combiner');
      
      const moduleHeight = 140; // Approximate height of extracted data modules
      const moduleSpacing = 20; // Space between modules
      const startY = 100; // Starting Y position
      const leftX = 200; // X position for extracted data modules
      const middleX = 600; // X position for type coercion module
      const rightX = 1000; // X position for data combiner module
      
      const initialModules: PlacedModule[] = [];
      
      // Add extracted data modules
      extractedDataModules.forEach((template, index) => {
        const config = {};
        const nodes = initializeModuleNodes(template, config);
        
        const module: PlacedModule = {
          id: `auto_${template.id}_${Date.now()}_${index}`,
          template,
          position: {
            x: leftX,
            y: startY + (index * (moduleHeight + moduleSpacing))
          },
          config,
          nodes
        };
        
        initialModules.push(module);
      });
      
      // Add Type Coercion module for testing
      if (typeCoercionModule) {
        // Initialize config with default values from template
        const config = {};
        typeCoercionModule.config.forEach(configField => {
          if (configField.defaultValue !== undefined) {
            config[configField.name] = configField.defaultValue;
          }
        });
        
        const nodes = initializeModuleNodes(typeCoercionModule, config);
        
        const module: PlacedModule = {
          id: `auto_type_coercion_${Date.now()}`,
          template: typeCoercionModule,
          position: {
            x: middleX,
            y: startY
          },
          config,
          nodes
        };
        
        initialModules.push(module);
      }
      
      // Add Data Combiner module for testing variable nodes
      if (dataCombinerModule) {
        // Initialize config with default values from template
        const config = {};
        dataCombinerModule.config.forEach(configField => {
          if (configField.defaultValue !== undefined) {
            config[configField.name] = configField.defaultValue;
          }
        });
        
        const nodes = initializeModuleNodes(dataCombinerModule, config);
        
        const module: PlacedModule = {
          id: `auto_data_combiner_${Date.now()}`,
          template: dataCombinerModule,
          position: {
            x: rightX,
            y: startY + 200
          },
          config,
          nodes
        };
        
        initialModules.push(module);
      }
      
      setPlacedModules(initialModules);
    }
  }, []);  // Empty dependency array to run only on initial render
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  
  // Placement state
  const [isPlacingModule, setIsPlacingModule] = useState(false);
  const [placementStartPos, setPlacementStartPos] = useState({ x: 0, y: 0 });

  // Module dragging state
  const [isDraggingModule, setIsDraggingModule] = useState(false);
  const [draggedModuleId, setDraggedModuleId] = useState<string | null>(null);
  const [moduleDragOffset, setModuleDragOffset] = useState({ x: 0, y: 0 });

  // Connection state
  const [connections, setConnections] = useState<NodeConnection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<string | null>(null);
  const [startingConnection, setStartingConnection] = useState<StartingConnection | null>(null);
  const [currentMousePosition, setCurrentMousePosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Node position tracking - stores actual DOM positions of node circles
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
  const initializeModuleNodes = (template: BaseModuleTemplate, config: any): ModuleNodeState => {
    let inputs: NodeState[] = [];
    let outputs: NodeState[] = [];
    
    // Use generateNodes if available for dynamic modules
    if (template.generateNodes) {
      const generated = template.generateNodes(config);
      inputs = generated.inputs.map((input, index) => ({
        id: `${template.id}_input_${index}`,
        type: input.type,
        description: input.description,
        required: input.required
      }));
      outputs = generated.outputs.map((output, index) => ({
        id: `${template.id}_output_${index}`,
        name: '',
        type: output.type,
        description: output.description,
        required: output.required || false
      }));
    } else {
      // Use template nodes for static modules
      inputs = template.inputs.map((input, index) => ({
        id: `${template.id}_input_${index}`,
        type: input.type,
        description: input.description,
        required: input.required
      }));
      outputs = template.outputs.map((output, index) => ({
        id: `${template.id}_output_${index}`,
        name: '',
        type: output.type,
        description: output.description,
        required: false
      }));
    }
    
    return { inputs, outputs };
  };
  
  // Helper function to get current inputs for a module
  const getModuleInputs = (module: PlacedModule): NodeState[] => {
    return module.nodes.inputs;
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

  // Helper function to get current outputs for a module
  const getModuleOutputs = (module: PlacedModule): NodeState[] => {
    return module.nodes.outputs;
  };

  // Helper function to create a new node from template with index replacement
  const createNodeFromTemplate = (template: ModuleInput | ModuleOutput, index: number, isInput: boolean) => {
    const nodeType = isInput ? 'input' : 'output';
    const node = {
      ...template,
      name: isInput ? undefined : '', // Only outputs get blank names, inputs get no name property
      description: template.description.replace('{{index}}', (index + 1).toString())
    };
    
    // Update dynamicType configKey if it exists
    if (node.dynamicType) {
      node.dynamicType = {
        ...node.dynamicType,
        configKey: node.dynamicType.configKey.replace('{{index}}', (index + 1).toString())
      };
    }
    
    return node;
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
        required: template.required
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
        name: '',
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
        
        return {
          ...module,
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

  // Calculate adaptive grid size based on zoom level
  const getGridSize = (zoomLevel: number) => {
    if (zoomLevel <= 0.25) {
      return 100; // Large grid for very zoomed out
    } else if (zoomLevel <= 0.5) {
      return 50; // Medium grid for moderately zoomed out
    } else {
      return 20; // Fine grid for normal/zoomed in
    }
  };

  // Calculate grid opacity based on zoom level
  const getGridOpacity = (zoomLevel: number) => {
    if (zoomLevel <= 0.25) {
      return 0.2; // Less visible when very zoomed out
    } else if (zoomLevel <= 0.5) {
      return 0.25; // Slightly more visible
    } else {
      return 0.3; // Normal visibility
    }
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
    setZoom(1);
    setPanOffset({ x: 0, y: 0 });
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
    setPlacementStartPos({ x: clickX, y: clickY });
    
    // Initialize config with default values from template
    const config = {};
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
      setSelectedModuleTemplate(null);
      setIsPlacingModule(false);
    }
    
    // DO NOT stop dragging here - let global handlers manage that
  };

  // Handle mouse leave - only for module placement, not for dragging (global handlers manage dragging)
  const handleCanvasMouseLeave = () => {
    // Only handle module placement cleanup, NOT dragging
    if (isPlacingModule) {
      setSelectedModuleTemplate(null);
      setIsPlacingModule(false);
    }
    
    // DO NOT stop dragging here - let global handlers manage that
  };

  // Module selection handlers
  const handleModuleTemplateSelect = (template: BaseModuleTemplate | null) => {
    setSelectedModuleTemplate(template);
  };

  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => !prev);
  };

  // Wheel event handler for zoom
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

    if (canvasRef.current) {
      canvasRef.current.addEventListener('wheel', handleWheel, { passive: false });
    }

    return () => {
      if (canvasRef.current) {
        canvasRef.current.removeEventListener('wheel', handleWheel);
      }
    };
  }, [isDraggingModule]);

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
  const handleModuleConfigChange = (moduleId: string) => (config: Record<string, any>) => {
    setPlacedModules(prev => 
      prev.map(module => {
        if (module.id === moduleId) {
          const updatedModule = { ...module, config };
          
          // If module has generateNodes, update node state
          if (module.template.generateNodes) {
            const generated = module.template.generateNodes(config);
            updatedModule.nodes = {
              inputs: generated.inputs.map((input, index) => ({
                id: `${module.id}_input_${index}`,
                name: input.name,
                type: input.type,
                description: input.description,
                required: input.required
              })),
              outputs: generated.outputs.map((output, index) => ({
                id: `${module.id}_output_${index}`,
                name: output.name,
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

  // Handle module click (selection)
  const handleModuleClick = (moduleId: string) => (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedModuleId(moduleId);
    
    // Clear selected connection when clicking on a module
    if (selectedConnectionId) {
      setSelectedConnectionId(null);
    }
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

  // Get node position from DOM-measured positions
  const getNodePosition = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number): { x: number; y: number } => {
    const nodeKey = `${moduleId}-${nodeType}-${nodeIndex}`;
    const position = nodePositions[nodeKey];
    
    if (position) {
      // Convert from screen coordinates to canvas coordinates
      const canvasRect = canvasRef.current?.getBoundingClientRect();
      if (canvasRect) {
        const canvasX = (position.x - canvasRect.left - panOffset.x) / zoom;
        const canvasY = (position.y - canvasRect.top - panOffset.y) / zoom;
        return { x: canvasX, y: canvasY };
      }
    }
    
    // Fallback to module center if position not yet measured
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
      const moduleData = JSON.parse(e.dataTransfer.getData('application/json')) as BaseModuleTemplate;
      const canvasRect = canvasRef.current.getBoundingClientRect();
      
      // Calculate drop position relative to canvas, accounting for zoom and pan
      const dropX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
      const dropY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
      
      // Initialize config with default values from template
      const config = {};
      moduleData.config.forEach(configField => {
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
      setSelectedModuleTemplate(null);
      
    } catch (error) {
      console.error('Failed to parse dropped module data:', error);
    }
  };

  return (
    <div className="relative w-full h-full overflow-hidden bg-gray-900 flex">
      {/* Module Selection Sidebar */}
      <div className={`relative z-50 ${isDragging ? 'pointer-events-none' : ''}`}>
        <ModuleSelectionPane
          modules={testBaseModules}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={toggleSidebar}
          onModuleSelect={handleModuleTemplateSelect}
          selectedModule={selectedModuleTemplate}
        />
      </div>

      {/* Main Graph Area */}
      <div className="flex-1 relative">
        {/* Connection Counter - Top Left */}
        <div className="absolute top-4 left-4 z-20 bg-gray-800 rounded-lg shadow-lg border border-gray-700 px-4 py-2">
          <div className="text-white text-sm font-medium">
            Connections: <span className="text-blue-400">{connections.length}</span>
          </div>
          {startingConnection && (
            <div className="text-green-400 text-xs mt-1">
              Creating connection...
            </div>
          )}
        </div>

        {/* Zoom Controls - Top Right */}
        <div className="absolute top-4 right-4 z-20 flex flex-col bg-gray-800 rounded-lg shadow-lg border border-gray-700">
          <button
            onClick={isDraggingModule ? undefined : zoomIn}
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
            onClick={isDraggingModule ? undefined : zoomOut}
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
            onClick={isDraggingModule ? undefined : resetZoom}
            disabled={isDraggingModule}
            className={`w-10 h-10 flex items-center justify-center transition-colors rounded-b-lg ${
              isDraggingModule 
                ? 'text-gray-500 cursor-not-allowed' 
                : 'text-white hover:bg-gray-700'
            }`}
            title={isDraggingModule ? "Cannot reset while dragging" : "Reset Zoom"}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>

        {/* Canvas Container */}
        <div
          ref={canvasRef}
          className={`w-full h-full select-none ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
          style={{
            userSelect: 'none',
            WebkitUserSelect: 'none',
            MozUserSelect: 'none',
            msUserSelect: 'none'
          }}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseLeave}
          onDragOver={handleCanvasDragOver}
          onDrop={handleCanvasDrop}
          style={{
            backgroundImage: `
              linear-gradient(rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px),
              linear-gradient(90deg, rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px)
            `,
            backgroundSize: `${getGridSize(zoom) * zoom}px ${getGridSize(zoom) * zoom}px`,
            backgroundPosition: `${panOffset.x}px ${panOffset.y}px`,
          }}
        >
          {/* Zoom and Pan Container */}
          <div
            className="relative w-full h-full origin-top-left"
            style={{
              transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`,
            }}
          >
            {/* CSS Animation for dashed lines */}
            <style>
              {`
                @keyframes dashAnimation {
                  0% {
                    stroke-dashoffset: 0;
                  }
                  100% {
                    stroke-dashoffset: -24;
                  }
                }
              `}
            </style>

            {/* Connection SVG Layer - Behind modules */}
            <svg
              className="absolute inset-0"
              style={{
                width: '100%',
                height: '100%',
                overflow: 'visible',
                pointerEvents: 'auto', // Allow pointer events for connection selection
                zIndex: 1 // Behind modules
              }}
            >
              {/* SVG Filters and Definitions */}
              <defs>
                <filter id="connectionGlow" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
                  <feMerge> 
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              {/* Existing Connections */}
              {connections.map((connection) => {
                const startPos = getNodePosition(connection.fromModuleId, 'output', connection.fromOutputIndex);
                const endPos = getNodePosition(connection.toModuleId, 'input', connection.toInputIndex);
                const path = generateBezierPath(startPos, endPos);
                
                // Get color from the output node type (source of the connection)
                const outputNodeType = getNodeType(connection.fromModuleId, 'output', connection.fromOutputIndex);
                const connectionColor = getTypeColor(outputNodeType);
                const isSelected = selectedConnectionId === connection.id;
                
                return (
                  <g key={connection.id}>
                    {isSelected ? (
                      <>
                        {/* Glow effect for selected connection */}
                        <path
                          d={path}
                          stroke={connectionColor}
                          strokeWidth="8"
                          fill="none"
                          strokeLinecap="round"
                          pointerEvents="none"
                          opacity="0.4"
                          filter="url(#connectionGlow)"
                        />
                        {/* Main connection path with animated dashes */}
                        <path
                          d={path}
                          stroke={connectionColor}
                          strokeWidth="3"
                          fill="none"
                          strokeLinecap="round"
                          strokeDasharray="8,4"
                          style={{ 
                            cursor: 'pointer',
                            animation: 'dashAnimation 2s linear infinite'
                          }}
                          onClick={handleConnectionClick(connection.id)}
                          onMouseDown={(e) => e.stopPropagation()}
                        />
                      </>
                    ) : (
                      /* Normal connection path */
                      <path
                        d={path}
                        stroke={connectionColor}
                        strokeWidth="2"
                        fill="none"
                        strokeLinecap="round"
                        style={{ cursor: 'pointer' }}
                        onClick={handleConnectionClick(connection.id)}
                        onMouseDown={(e) => e.stopPropagation()}
                      />
                    )}
                    {/* Invisible thicker path for easier clicking */}
                    <path
                      d={path}
                      stroke="transparent"
                      strokeWidth="10"
                      fill="none"
                      strokeLinecap="round"
                      style={{ cursor: 'pointer' }}
                      onClick={handleConnectionClick(connection.id)}
                      onMouseDown={(e) => e.stopPropagation()}
                    />
                  </g>
                );
              })}

              {/* Preview Connection */}
              {startingConnection && (() => {
                const startingNodeType = getNodeType(startingConnection.moduleId, startingConnection.type, startingConnection.index);
                const previewColor = getTypeColor(startingNodeType);
                
                return (
                  <path
                    d={generateBezierPath(
                      getNodePosition(startingConnection.moduleId, startingConnection.type, startingConnection.index),
                      currentMousePosition,
                      startingConnection.type
                    )}
                    stroke={previewColor}
                    strokeWidth="2"
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray="5,5"
                  />
                );
              })()}

              {/* Debug: Show calculated node positions */}
              {placedModules.map((module) => (
                <g key={`debug-${module.id}`}>
                  {/* Input node position indicators */}
                  {module.nodes.inputs.map((input, index) => {
                    const pos = getNodePosition(module.id, 'input', index);
                    return (
                      <circle
                        key={`debug-input-${index}`}
                        cx={pos.x}
                        cy={pos.y}
                        r="3"
                        fill="red"
                        opacity="0.7"
                        pointerEvents="none"
                      />
                    );
                  })}
                  {/* Output node position indicators */}
                  {module.nodes.outputs.map((output, index) => {
                    const pos = getNodePosition(module.id, 'output', index);
                    return (
                      <circle
                        key={`debug-output-${index}`}
                        cx={pos.x}
                        cy={pos.y}
                        r="3"
                        fill="yellow"
                        opacity="0.7"
                        pointerEvents="none"
                      />
                    );
                  })}
                </g>
              ))}
            </svg>

            {/* Placed Modules - In front of connections */}
            <div style={{ position: 'relative', zIndex: 2 }}>
              {placedModules.map((placedModule) => {
                // Use new state-based component for all modules
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
                      onMouseDown={handleModuleMouseDown(placedModule.id)}
                      onDelete={handleModuleDelete(placedModule.id)}
                      onConfigChange={handleModuleConfigChange(placedModule.id)}
                      onNodeClick={handleNodeClick}
                      onNodePositionUpdate={handleNodePositionUpdate}
                    />
                  );
                }
                
                // Use new state-based component for all other modules
                return (
                  <NewGraphModuleComponent
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
                    onMouseDown={handleModuleMouseDown(placedModule.id)}
                    onDelete={handleModuleDelete(placedModule.id)}
                    onConfigChange={handleModuleConfigChange(placedModule.id)}
                    onNodeClick={handleNodeClick}
                    onAddInput={handleAddInput}
                    onRemoveInput={handleRemoveInput}
                    onAddOutput={handleAddOutput}
                    onRemoveOutput={handleRemoveOutput}
                    onNodeTypeChange={handleNodeTypeChange}
                    onNodePositionUpdate={handleNodePositionUpdate}
                    onNameChange={handleNodeNameChange}
                    getInputDisplayName={getInputDisplayName}
                    canChangeType={canNodeChangeType}
                  />
                );
              })}
            </div>
          </div>
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
                      handleConnectionDelete(selectedConnectionId);
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
      </div>
    </div>
  );
}