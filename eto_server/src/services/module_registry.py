"""
Module Registry Service
Discovers, loads, and manages transformation module implementations
"""
import os
import importlib
import inspect
import logging
from typing import Dict, Any, List, Type, Optional
from pathlib import Path

from ..modules.module import BaseModuleExecutor as BaseModule

logger = logging.getLogger(__name__)

class ModuleRegistry:
    """Registry for managing transformation modules"""
    
    def __init__(self):
        self.modules: Dict[str, BaseModule] = {}
        self.module_info: Dict[str, Dict[str, Any]] = {}
        self._loaded = False
    
    def discover_modules(self) -> None:
        """Discover and load all module implementations"""
        logger.info("Discovering transformation modules...")
        
        # Get the implementations directory
        current_dir = Path(__file__).parent.parent
        implementations_dir = current_dir / "modules" / "implementations"
        
        if not implementations_dir.exists():
            logger.warning(f"Module implementations directory not found: {implementations_dir}")
            return
        
        # Walk through all subdirectories and Python files
        for root, dirs, files in os.walk(implementations_dir):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    self._load_module_from_file(Path(root) / file)
        
        logger.info(f"Discovered {len(self.modules)} modules")
        self._loaded = True
    
    def _load_module_from_file(self, file_path: Path) -> None:
        """Load a module from a Python file"""
        try:
            # Convert file path to module import path
            relative_path = file_path.relative_to(Path(__file__).parent.parent)
            module_path = str(relative_path).replace(os.sep, '.').replace('.py', '')
            
            logger.debug(f"Loading module from: {module_path}")
            
            # Import the module
            module = importlib.import_module(f"..{module_path}", __name__)
            
            # Find BaseModule subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseModule) and 
                    obj != BaseModule and 
                    not inspect.isabstract(obj)):
                    
                    # Instantiate the module
                    module_instance = obj()
                    module_id = module_instance.module_id
                    
                    logger.info(f"Registered module: {module_id} ({module_instance.name})")
                    
                    self.modules[module_id] = module_instance
                    self.module_info[module_id] = module_instance.get_module_info()
                    break
                    
        except Exception as e:
            logger.error(f"Failed to load module from {file_path}: {e}")
    
    def get_module(self, module_id: str) -> Optional[BaseModule]:
        """Get a module instance by ID"""
        if not self._loaded:
            self.discover_modules()
        return self.modules.get(module_id)
    
    def get_all_modules(self) -> Dict[str, BaseModule]:
        """Get all registered modules"""
        if not self._loaded:
            self.discover_modules()
        return self.modules.copy()
    
    def get_module_info(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get module information by ID"""
        if not self._loaded:
            self.discover_modules()
        return self.module_info.get(module_id)
    
    def get_all_module_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information for all modules"""
        if not self._loaded:
            self.discover_modules()
        return self.module_info.copy()
    
    def execute_module(self, module_id: str, inputs: Dict[str, Any], 
                      config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a module by ID"""
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return await module.execute(inputs, config)
    
    def reload_modules(self) -> None:
        """Reload all modules (for development)"""
        logger.info("Reloading all modules...")
        self.modules.clear()
        self.module_info.clear()
        self._loaded = False
        self.discover_modules()

# Global registry instance
_registry = None

def get_module_registry() -> ModuleRegistry:
    """Get the global module registry instance"""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry