from abc import ABC, abstractmethod
from typing import List, Dict

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.infrastructure.mcp.config_utils import extract_mcp_server_config


class ToolManager(ABC):
    """工具类管理基类"""

    @abstractmethod
    async def get_tools(self, agent_type: str, config: RunnableConfig) -> List[BaseTool]:
        """工具管理器基类"""
        pass

class MCPToolManager(ToolManager):

    def __init__(self):
        self._mcp_clients: dict[str, MultiServerMCPClient] = {}

    async def get_tools(self, agent_type: str, config: RunnableConfig) -> List[BaseTool]:
        tools = []
        configurable = config.get("configurable",{})
        mcp_settings = configurable.get("mcp_settings",{})

        if mcp_settings:
            return tools

        mcp_servers = self._extract_mcp_servers_for_agent(mcp_settings, agent_type)

        if mcp_servers:
            client = await self._get_or_create_client(mcp_servers)
            mcp_tools = await client.get_tools()

            for mcp_tool in mcp_tools:
                tools.append(mcp_tool)

        return tools

    def _extract_mcp_servers_for_agent(self, mcp_settings: Dict, agent_type: str):
        mcp_servers = {}

        for server_name, server_config in mcp_settings.items():
            mcp_servers[server_name] = extract_mcp_server_config(server_config)

        return mcp_servers

    async def _get_or_create_client(self, mcp_servers: Dict) -> MultiServerMCPClient:
        server_key = str(sorted(mcp_servers.items()))

        if server_key not in self._mcp_clients:
            self._mcp_clients[server_key] = MultiServerMCPClient(mcp_servers)

        return self._mcp_clients[server_key]


class DefaultToolManager(ToolManager):

    def __init__(self, tool_registry: Dict[str, List[BaseTool]]):
        self.tool_registry = tool_registry

    async def get_tools(self, agent_type: str, config: RunnableConfig) -> List[BaseTool]:
        return self.tool_registry.get(agent_type, [])
