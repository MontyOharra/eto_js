"""Module definitions exceptions"""


class ModuleDefinitionError(Exception):
    """Base repository exception"""
    pass


class NotImplementedError(ModuleDefinitionError):
    """Module run function not implemented"""
    pass