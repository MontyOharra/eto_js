"""
Pipeline Execution Exceptions
Custom exceptions for pipeline execution errors
"""


class PipelineExecutionError(Exception):
    """Base exception for pipeline execution errors"""
    pass


class ModuleExecutionError(PipelineExecutionError):
    """Exception raised when a module fails during execution"""

    def __init__(self, module_instance_id: str, message: str):
        self.module_instance_id = module_instance_id
        self.message = message
        super().__init__(f"Module '{module_instance_id}' failed: {message}")
