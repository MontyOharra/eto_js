"""
Type definitions for ETO Transformation Pipeline Server

This module contains all type definitions, aliases, and protocols used throughout
the transformation pipeline system for better type safety and IDE support.
"""

from typing import Dict, List, Optional, Union, Any, Protocol, TypedDict, NotRequired, Literal
from abc import abstractmethod

# Basic type aliases
ModuleID = str
NodeType = Literal['string', 'number', 'boolean', 'datetime']
ModuleCategory = Literal['Text Processing', 'AI/ML', 'Data Processing', \
                         'Module Definers', 'Testing']

# Input/Output Schema Types
class NodeSchema(TypedDict):
    """Schema for node creation - defines defaults when node is created"""
    defaultName: str  # Default name when node is created (user can change)
    type: NodeType    # Default type when node is created

class ConfigSchema(TypedDict):
    """Schema for a configuration option"""
    name: str
    type: str  # 'string', 'number', 'boolean', 'select', 'textarea'
    description: str
    required: bool
    defaultValue: NotRequired[Any]
    options: NotRequired[List[str]]  # For select type

# Dynamic Node Configuration
class DynamicNodeConfig(TypedDict):
    """Configuration for dynamic node behavior"""
    maxNodes: Optional[int]  # Maximum nodes allowed (None = unlimited)
    defaultNode: NodeSchema  # Template for new nodes when user adds them

class NodeConfiguration(TypedDict):
    """Complete configuration for inputs or outputs of a module"""
    # Base nodes - automatically created when module is instantiated
    nodes: List[NodeSchema]
    
    # Dynamic behavior - None means static node count
    dynamic: Optional[DynamicNodeConfig]
    
    # Type constraints
    allowedTypes: List[NodeType]  # Empty array = all types allowed
                                 # Single item = type locked  
                                 # Multiple items = user can choose from these

# Module Information Types
class ModuleInfo(TypedDict):
    """Complete module information for database storage"""
    id: ModuleID
    name: str
    description: str
    version: str
    # New consolidated configuration
    input_config: str   # JSON string of NodeConfiguration
    output_config: str  # JSON string of NodeConfiguration
    config_schema: str  # JSON string of List[ConfigSchema]
    service_endpoint: Optional[str]
    handler_name: str
    color: str
    category: ModuleCategory
    is_active: bool

class FrontendModuleInfo(TypedDict):
    """Module information formatted for frontend consumption"""
    id: ModuleID
    name: str
    description: str
    category: ModuleCategory
    color: str
    version: str
    # New consolidated configuration
    inputConfig: NodeConfiguration
    outputConfig: NodeConfiguration
    config: List[ConfigSchema]

# Execution Types
class ExecutionInputs(Dict[str, Any]):
    """Type for module execution inputs"""
    pass

class ExecutionOutputs(Dict[str, Any]):
    """Type for module execution outputs"""
    pass

class ExecutionConfig(Dict[str, Any]):
    """Type for module execution configuration"""
    pass

# Node Type Information
class NodeTypeInfo(TypedDict):
    """Type information for a specific node"""
    nodeId: str
    type: NodeType

class ExecutionNodeInfo(TypedDict):
    """Node type information for execution context"""
    inputs: List[NodeTypeInfo]   # Input node IDs and their types
    outputs: List[NodeTypeInfo]  # Expected output node IDs and their types

# Pipeline Types
class PipelineNode(TypedDict):
    """Node in a pipeline"""
    id: str
    name: str
    type: NodeType
    description: str
    required: bool

class PipelineModuleNodes(TypedDict):
    """Input and output nodes for a pipeline module"""
    inputs: List[PipelineNode]
    outputs: List[PipelineNode]

class PipelineModule(TypedDict):
    """Module in a pipeline"""
    id: str
    templateId: ModuleID
    template: Dict[str, Any]  # Simplified template info
    position: Dict[str, float]  # {x: float, y: float}
    config: ExecutionConfig
    nodes: PipelineModuleNodes

class ConnectionSource(TypedDict):
    """Source endpoint of a pipeline connection (output)"""
    moduleId: str
    outputIndex: int

class ConnectionTarget(TypedDict):
    """Target endpoint of a pipeline connection (input)"""
    moduleId: str
    inputIndex: int

class PipelineConnection(TypedDict):
    """Connection between modules in a pipeline"""
    id: str
    source: ConnectionSource
    target: ConnectionTarget

class PipelineData(TypedDict):
    """Complete pipeline data structure"""
    modules: List[PipelineModule]
    connections: List[PipelineConnection]

# Transformation Step Types
class TransformationStep(TypedDict):
    """Single step in a transformation pipeline"""
    step_number: int
    template_id: ModuleID
    module_id: str
    input_field: str
    output_field: str
    config: ExecutionConfig

class PipelineAnalysisResult(TypedDict):
    """Result from pipeline analysis"""
    success: bool
    transformation_steps: List[TransformationStep]
    field_mappings: Dict[str, str]
    total_steps: int
    error: NotRequired[str]

# Module Execution Protocol
class ModuleExecutor(Protocol):
    """Protocol for module executors"""
    
    @abstractmethod
    def get_module_id(self) -> ModuleID:
        """Return the unique module ID"""
        ...
    
    @abstractmethod
    def get_module_info(self) -> ModuleInfo:
        """Return the module template information for database storage"""
        ...
    
    @abstractmethod
    def execute(self, inputs: ExecutionInputs, config: ExecutionConfig, 
                output_names: Optional[List[str]] = None) -> ExecutionOutputs:
        """Execute the module with given inputs and configuration"""
        ...
    
    def validate_inputs(self, inputs: ExecutionInputs) -> bool:
        """Validate inputs for this module"""
        return True
    
    def validate_config(self, config: ExecutionConfig) -> bool:
        """Validate configuration for this module"""
        return True

# Database Service Protocol
class DatabaseService(Protocol):
    """Protocol for database service"""
    
    def get_session(self):
        """Get a new database session"""
        ...
    
    def create_tables(self) -> None:
        """Create all database tables"""
        ...
    
    def close(self) -> None:
        """Close the database engine"""
        ...

# API Response Types
class ApiResponse(TypedDict):
    """Base API response"""
    success: bool
    message: NotRequired[str]
    error: NotRequired[str]

class ModulesApiResponse(ApiResponse):
    """API response for modules endpoint"""
    modules: List[FrontendModuleInfo]

class ModuleExecutionResponse(ApiResponse):
    """API response for module execution"""
    outputs: NotRequired[ExecutionOutputs]

class PipelineAnalysisResponse(ApiResponse):
    """API response for pipeline analysis"""
    transformation_steps: NotRequired[List[TransformationStep]]
    field_mappings: NotRequired[Dict[str, str]]
    total_steps: NotRequired[int]

# Error Types
class ModuleError(Exception):
    """Base exception for module-related errors"""
    pass

class ModuleExecutionError(ModuleError):
    """Raised when module execution fails"""
    pass

class ModuleValidationError(ModuleError):
    """Raised when module validation fails"""
    pass

class PipelineAnalysisError(Exception):
    """Raised when pipeline analysis fails"""
    pass

class PipelineExecutionError(Exception):
    """Raised when pipeline execution fails"""
    pass