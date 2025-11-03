"""Module definitions exceptions"""


class ModuleDefinitionError(Exception):
    """Base repository exception"""
    pass


class NotImplementedError(ModuleDefinitionError):
    """Module run function not implemented"""

    def __init__(self, module_id: str, module_class_name: str):
        """
        Initialize NotImplementedError with module information

        Args:
            module_id: Module ID (e.g., "boolean_and:1.0.0")
            module_class_name: Module class name (e.g., "BooleanAnd")
        """
        if module_id and module_class_name:
            message = f"Module '{module_id}' ({module_class_name}) has not implemented the run() method"
        elif module_id:
            message = f"Module '{module_id}' has not implemented the run() method"
        elif module_class_name:
            message = f"Module class '{module_class_name}' has not implemented the run() method"
        else:
            message = "Module has not implemented the run() method"

        self.module_id = module_id
        self.module_class_name = module_class_name
        super().__init__(message)