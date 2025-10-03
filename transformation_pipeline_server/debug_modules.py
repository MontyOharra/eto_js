"""
Debug script to check module definitions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.features.modules.core.registry import get_registry, auto_discover_modules

# Clear any cached modules
modules_to_clear = [
    key for key in sys.modules.keys()
    if key.startswith("src.features.modules.")
]
for module_name in modules_to_clear:
    del sys.modules[module_name]

# Discover modules
packages_to_scan = [
    "src.features.modules.transform",
    "src.features.modules.action",
    "src.features.modules.logic",
]
auto_discover_modules(packages_to_scan)

# Get registry
registry = get_registry()
modules = registry.get_all()

print(f"\nFound {len(modules)} modules:\n")

for module_id, module_class in modules.items():
    print(f"\nModule: {module_id}")
    print(f"  Class: {module_class.__name__}")

    try:
        meta = module_class.meta()
        print(f"  Meta inputs type: {meta.inputs.type} (type: {type(meta.inputs.type)})")
        print(f"  Meta outputs type: {meta.outputs.type} (type: {type(meta.outputs.type)})")

        # Check the raw dict format
        meta_dict = meta.model_dump()
        print(f"  Meta dict inputs type: {meta_dict['inputs']['type']} (type: {type(meta_dict['inputs']['type'])})")
        print(f"  Meta dict outputs type: {meta_dict['outputs']['type']} (type: {type(meta_dict['outputs']['type'])})")
    except Exception as e:
        print(f"  Error getting meta: {e}")