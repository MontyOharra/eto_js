"""
Modules Service - Management of transformation pipeline modules
Handles module discovery, registration, and execution
"""
import logging
from typing import Dict, List, Optional, Type, Any
from .core.contracts import CommonCore, TransformModule, ActionModule, LogicModule

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    Registry for transformation pipeline modules
    Manages module registration and discovery
    """

    def __init__(self):
        self._modules: Dict[str, Type[CommonCore]] = {}
        logger.info("ModuleRegistry initialized")

    def register_module(self, module_class: Type[CommonCore]) -> None:
        """
        Register a module class in the registry

        Args:
            module_class: Module class that extends CommonCore
        """
        module_ref = f"{module_class.id}:{module_class.version}"

        if module_ref in self._modules:
            logger.warning(f"Module {module_ref} already registered, overwriting")

        self._modules[module_ref] = module_class
        logger.info(f"Registered module: {module_ref} ({module_class.kind})")

    def get_module(self, module_ref: str) -> Optional[Type[CommonCore]]:
        """
        Get a module class by reference

        Args:
            module_ref: Module reference in format "id:version"

        Returns:
            Module class or None if not found
        """
        return self._modules.get(module_ref)

    def list_modules(self) -> Dict[str, Type[CommonCore]]:
        """
        List all registered modules

        Returns:
            Dictionary of module_ref -> module_class
        """
        return self._modules.copy()

    def list_modules_by_kind(self, kind: str) -> Dict[str, Type[CommonCore]]:
        """
        List modules filtered by kind

        Args:
            kind: Module kind ("transform", "action", "logic")

        Returns:
            Dictionary of module_ref -> module_class for matching kind
        """
        return {
            ref: module_class
            for ref, module_class in self._modules.items()
            if module_class.kind == kind
        }


class ModulesService:
    """
    Service for managing transformation pipeline modules
    Provides high-level interface for module operations
    """

    def __init__(self):
        self.registry = ModuleRegistry()
        logger.info("ModulesService initialized")

        # Auto-discover and register modules at startup
        self._auto_discover_modules()

    def _auto_discover_modules(self):
        """Auto-discover and register modules from known packages"""
        try:
            # Import the registry's auto-discover function
            from .core.registry import auto_discover_modules

            # List of packages to scan for modules
            packages_to_scan = [
                "src.features.modules.transform",
                "src.features.modules.action",
                "src.features.modules.logic",
                "src.features.modules.comparator"
            ]

            logger.info("Auto-discovering modules from packages...")
            auto_discover_modules(packages_to_scan)

            # Log discovered modules
            module_count = len(self.registry.list_modules())
            logger.info(f"Auto-discovery complete: {module_count} modules registered")

        except Exception as e:
            logger.error(f"Failed to auto-discover modules: {e}")
            # Don't fail initialization if auto-discovery fails
            logger.warning("ModulesService will continue without auto-discovered modules")

    def is_healthy(self) -> bool:
        """Health check for the modules service"""
        try:
            # Simple health check - verify registry is accessible
            module_count = len(self.registry.list_modules())
            logger.debug(f"ModulesService health check: {module_count} modules registered")
            return True
        except Exception as e:
            logger.error(f"ModulesService health check failed: {e}")
            return False

    def register_module(self, module_class: Type[CommonCore]) -> None:
        """
        Register a new module

        Args:
            module_class: Module class to register
        """
        self.registry.register_module(module_class)

    def get_module_catalog(self) -> List[Dict[str, Any]]:
        """
        Get catalog of all available modules for frontend/API consumption

        Returns:
            List of module metadata dictionaries
        """
        catalog = []

        for module_ref, module_class in self.registry.list_modules().items():
            meta = module_class.meta()

            catalog.append({
                "module_ref": module_ref,
                "id": module_class.id,
                "version": module_class.version,
                "title": module_class.title,
                "description": module_class.description,
                "kind": module_class.kind,
                "meta": meta.model_dump(),
                "config_schema": module_class.ConfigModel.model_json_schema()
            })

        return catalog

    def get_module_by_ref(self, module_ref: str) -> Optional[Type[CommonCore]]:
        """
        Get module class by reference

        Args:
            module_ref: Module reference "id:version"

        Returns:
            Module class or None if not found
        """
        return self.registry.get_module(module_ref)

    def create_module_instance(self, module_ref: str) -> Optional[CommonCore]:
        """
        Create an instance of a module

        Args:
            module_ref: Module reference "id:version"

        Returns:
            Module instance or None if module not found
        """
        module_class = self.registry.get_module(module_ref)
        if module_class is None:
            logger.error(f"Module not found: {module_ref}")
            return None

        try:
            instance = module_class()
            logger.debug(f"Created instance of {module_ref}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create instance of {module_ref}: {e}")
            return None

    def validate_module_config(self, module_ref: str, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for a module

        Args:
            module_ref: Module reference "id:version"
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid
        """
        module_class = self.registry.get_module(module_ref)
        if module_class is None:
            logger.error(f"Module not found for validation: {module_ref}")
            return False

        try:
            # Validate using Pydantic model
            module_class.ConfigModel.model_validate(config)
            return True
        except Exception as e:
            logger.warning(f"Config validation failed for {module_ref}: {e}")
            return False

    def execute_module(self,
                      module_ref: str,
                      inputs: Dict[str, Any],
                      config: Dict[str, Any],
                      context: Any = None) -> Optional[Dict[str, Any]]:
        """
        Execute a module with given inputs and configuration

        Args:
            module_ref: Module reference "id:version"
            inputs: Input values keyed by node ID
            config: Configuration values
            context: Execution context

        Returns:
            Output values or None if execution failed
        """
        # Create module instance
        module = self.create_module_instance(module_ref)
        if module is None:
            return None

        # Validate and parse configuration
        if not self.validate_module_config(module_ref, config):
            logger.error(f"Invalid configuration for {module_ref}")
            return None

        try:
            # Create validated config model
            module_class = self.registry.get_module(module_ref)
            validated_config = module_class.ConfigModel.model_validate(config)

            # Execute module
            logger.debug(f"Executing {module_ref} with {len(inputs)} inputs")
            outputs = module.run(inputs, validated_config, context)
            logger.debug(f"Module {module_ref} produced {len(outputs)} outputs")

            return outputs

        except Exception as e:
            logger.error(f"Module execution failed for {module_ref}: {e}")
            return None

    def get_module_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered modules

        Returns:
            Dictionary with module statistics
        """
        all_modules = self.registry.list_modules()

        stats = {
            "total_modules": len(all_modules),
            "transform_modules": len(self.registry.list_modules_by_kind("transform")),
            "action_modules": len(self.registry.list_modules_by_kind("action")),
            "logic_modules": len(self.registry.list_modules_by_kind("logic")),
            "module_refs": list(all_modules.keys())
        }

        return stats