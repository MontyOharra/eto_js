import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef, useEffect, useCallback } from "react";
import { ModuleSelectionPane } from "../../components/transformation-pipeline/ui/ModuleSelectionPane";
import { ExtractedDataModuleComponent } from "../../components/transformation-pipeline/modules/ExtractedDataModuleComponent";
import { GraphModule } from "../../components/transformation-pipeline/modules/GraphModule";
import { BaseModuleTemplate } from "../../types/modules";
import { useTransformationModules } from "../../hooks/useTransformationModules";
import { analyzePipeline, executeModule } from "../../services/transformationPipelineApi";
import { mockExtractedFields } from "../../data/testModules";

export const Route = createFileRoute("/transformation_pipeline/graph")({
  component: TransformationPipelineGraph,
});

interface NodeState {
  id: string;
  name: string; // Required name to match component interface
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
  config: Record<string, unknown>;
  
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
  // Load modules from both mock and backend
  const { modules: allModules, isLoading: modulesLoading, error: modulesError } = useTransformationModules();
  
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

  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  
  // Placement state
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

  // Helper function to format execution steps with input/output field names
  const formatExecutionSteps = (analysisResult: any) => {
    const steps: Array<{
      stepNumber: number;
      inputField: string;
      process: string;
      outputField: string;
    }> = [];

    if (!analysisResult.execution_plan?.steps) return steps;

    analysisResult.execution_plan.steps.forEach((step: any) => {
      step.modules.forEach((module: any) => {
        // Find the module in placed modules to get node information
        const placedModule = placedModules.find(pm => pm.id === module.id);
        if (!placedModule) return;

        // Get the module template to get the display name
        const template = placedModule.template;
        
        // For each connection involving this module, create execution steps
        connections.forEach((connection) => {
          if (connection.toModuleId === module.id) {
            // This module receives input from another module
            const fromModule = placedModules.find(pm => pm.id === connection.fromModuleId);
            if (!fromModule) return;

            // Get the input field name from the connected output (the actual data being passed)
            const inputField = fromModule.nodes.outputs[connection.fromOutputIndex]?.name || `Output ${connection.fromOutputIndex + 1}`;
            // Get the output field name from this module
            const outputField = placedModule.nodes.outputs[0]?.name || `Output 1`;
            
            steps.push({
              stepNumber: step.step_number,
              inputField: inputField,
              process: template.name,
              outputField: outputField
            });
          }
        });

        // For modules with no input connections (like extracted data modules), still show them
        const hasInputConnections = connections.some(conn => conn.toModuleId === module.id);
        if (!hasInputConnections && placedModule.nodes.outputs.length > 0) {
          const outputField = placedModule.nodes.outputs[0]?.name || `Output 1`;
          steps.push({
            stepNumber: step.step_number,
            inputField: "Source Data",
            process: template.name,
            outputField: outputField
          });
        }
      });
    });

    return steps;
  };

  // Handle pipeline run
  const handleRunPipeline = async () => {
    // Check if order generation module is present
    console.log(placedModules);
    const orderModule = placedModules.find(module => 
      module.template.id === 'order_generation'
    );
    
    if (!orderModule) {
      alert('Order Generation module is required to run the pipeline');
      return;
    }

    console.log('🚀 Executing transformation pipeline...');
    
    // Debug: Log current placed modules
    console.log('🔍 Debug - Current placed modules:', placedModules.map(m => ({
      id: m.id,
      templateId: m.template.id,
      category: m.template.category,
      nodes: m.nodes
    })));
    
    // Collect base inputs from extracted data modules
    const baseInputs: Record<string, any> = {};
    
    placedModules.forEach(module => {
      // Check if this is an extracted data module
      if (module.template.category === 'Extracted Data') {
        if (module.nodes.outputs.length > 0) {
          const outputFieldName = module.nodes.outputs[0].name;
          
          // First try to get value from module config (user-entered value)
          let value = module.config['test_value'];
          
          // If no user value, fall back to default sample value
          if (!value || value === '') {
            const fieldName = module.template.id.replace('extracted_', '');
            const extractedField = mockExtractedFields.find(field => field.name === fieldName);
            value = extractedField?.sampleValue || 'No value';
          }
          
          baseInputs[outputFieldName] = value;
          console.log(`📥 Base input: ${outputFieldName} = "${value}" (from ${module.config['test_value'] ? 'user config' : 'default sample'})`);
        }
      }
    });
    
    console.log('🔍 Debug - Final baseInputs:', baseInputs);
    
    // Prepare pipeline data for execution
    const pipelineData = {
      modules: placedModules.map(module => ({
        id: module.id,
        templateId: module.template.id.startsWith('backend_') 
          ? module.template.id.replace('backend_', '') 
          : module.template.id,
        config: module.config,
        position: module.position,
        nodes: module.nodes
      })),
      connections: connections.map(connection => ({
        from: { moduleId: connection.fromModuleId, outputIndex: connection.fromOutputIndex },
        to: { moduleId: connection.toModuleId, inputIndex: connection.toInputIndex }
      })),
      inputData: baseInputs
    };

    try {
      // Call transformation_pipeline_server API to execute pipeline
      console.log('📊 Pipeline data for execution:', pipelineData);
      
      const response = await fetch('http://localhost:8090/api/pipeline/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(pipelineData)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        console.log('✅ Pipeline execution completed successfully!');
        console.log('📋 Pipeline Analysis:', result.analysis);
        console.log('🎯 Final Output Data:', result.outputs);
        
        // Log the transformation steps that were executed
        if (result.analysis?.transformation_steps) {
          console.log('\n🔧 TRANSFORMATION STEPS EXECUTED:');
          console.log('=====================================');
          result.analysis.transformation_steps.forEach((step: any) => {
            console.log(`Step ${step.step_number}: ${step.input_field_name} → [${step.template_id}] → ${step.output_field_name}`);
            console.log(`    Internal IDs: ${step.input_field_id} → ${step.output_field_id}`);
          });
          console.log('=====================================\n');
        }
        
        // Log the field mappings for debugging
        if (result.analysis?.field_mappings) {
          console.log('\n🗺️ FIELD MAPPINGS:');
          console.log('=====================================');
          console.log('ID to Name:', result.analysis.field_mappings.id_to_name);
          console.log('Name to IDs:', result.analysis.field_mappings.name_to_ids);
          console.log('=====================================\n');
        }
        
        // Log the final output field names and values
        if (result.outputs && Object.keys(result.outputs).length > 0) {
          console.log('\n🎯 FINAL OUTPUT DATA:');
          console.log('=====================================');
          Object.entries(result.outputs).forEach(([fieldName, value]) => {
            console.log(`${fieldName}: "${value}"`);
          });
          console.log('=====================================\n');
        }
        
      } else {
        throw new Error(result.message || 'Pipeline execution failed');
      }
      
    } catch (error) {
      console.error('❌ Pipeline execution failed:', error);
      alert(`Pipeline execution failed: ${error instanceof Error ? error.message : 'Unknown error'}\n\nCheck console for details.`);
    }
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
      const moduleData = JSON.parse(e.dataTransfer.getData('application/json')) as BaseModuleTemplate;
      const canvasRect = canvasRef.current.getBoundingClientRect();
      
      // Calculate drop position relative to canvas, accounting for zoom and pan
      const dropX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
      const dropY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
      
      // Initialize config with default values from template
      const config: Record<string, unknown> = {};
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

  // Show loading state while modules are loading
  if (modulesLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading modules from backend...</p>
          {modulesError && <p className="text-red-400 mt-2">Error: {modulesError}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-gray-900 flex">
      {/* Module Selection Sidebar */}
      <div className={`relative z-50 ${isDragging ? 'pointer-events-none' : ''}`}>
        <ModuleSelectionPane
          modules={allModules}
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

        {/* Run Button - Top Center */}
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-20">
          <button
            onClick={handleRunPipeline}
            disabled={placedModules.length === 0}
            className={`px-6 py-3 rounded-lg shadow-lg border font-medium text-sm flex items-center gap-2 transition-colors ${
              placedModules.length === 0
                ? 'bg-gray-600 border-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700 border-green-500 text-white cursor-pointer'
            }`}
            title={placedModules.length === 0 ? 'Add modules to run pipeline' : 'Run transformation pipeline'}
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
            </svg>
            Run Pipeline
          </button>
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
            msUserSelect: 'none',
            backgroundImage: `
              linear-gradient(rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px),
              linear-gradient(90deg, rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px)
            `,
            backgroundSize: `${getGridSize(zoom) * zoom}px ${getGridSize(zoom) * zoom}px`,
            backgroundPosition: `${panOffset.x}px ${panOffset.y}px`,
          }}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseLeave}
          onDragOver={handleCanvasDragOver}
          onDrop={handleCanvasDrop}
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
                      (<path
                        d={path}
                        stroke={connectionColor}
                        strokeWidth="2"
                        fill="none"
                        strokeLinecap="round"
                        style={{ cursor: 'pointer' }}
                        onClick={handleConnectionClick(connection.id)}
                        onMouseDown={(e) => e.stopPropagation()}
                      />)
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
                )
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
                      isSidebarCollapsed={isSidebarCollapsed}
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
                  <GraphModule
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
                    isSidebarCollapsed={isSidebarCollapsed}
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
  )
}