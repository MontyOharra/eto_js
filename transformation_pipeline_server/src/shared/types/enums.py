from typing import Literal

AllowedModuleTypes = Literal["str", "float", "datetime", "bool", "int"]
ModuleKind = Literal["transform", "action", "logic", "comparator"]