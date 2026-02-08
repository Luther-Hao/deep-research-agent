from abc import ABC


class ToolManager(ABC):
    pass

class CompositeToolManager(ToolManager):
    pass

class MCPToolManager(ToolManager):
    pass

class DefaultToolManager(ToolManager):
    pass
