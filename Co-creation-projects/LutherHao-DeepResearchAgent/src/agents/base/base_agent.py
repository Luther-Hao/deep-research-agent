from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langsmith.schemas import Prompt

from src.agents.model.agent_info import AgentInfo
from src.agents.tool.tool_manager import ToolManager

from src.agents.llms.llm_manager import llm_manager as model_manager


class AgentType(Enum):
    SIMPLE_REACT = "simple_react"


class BaseAgent(ABC):
    """
    基于LangGraph的Agent基类
    """
    def __init__(self,
                 checkpointer:Optional[BaseCheckpointSaver] = None,
                 tool_manager:Optional[ToolManager] = None):
        self._checkpointer = checkpointer
        self._tool_manager = tool_manager
        self._compiled_graph:Optional[CompiledStateGraph] = None


    @classmethod
    @abstractmethod
    def get_info(cls) -> AgentInfo:
        """
        获取Agent的信息
        """
        pass

    @abstractmethod
    def build_graph(self):
        """构建图模型"""
        pass

    @abstractmethod
    async def build_graph_async(self,config:RunnableConfig) -> CompiledStateGraph:
        """异步构建，支持动态工具加载"""
        pass

    async def get_dynamic_tools(self, config: RunnableConfig = None):
        """获取动态工具"""
        agent_info = self.get_info()
        agent_type = agent_info.agent_type.value

        return await self._tool_manager.get_tools(agent_type, config)

    async def get_compiled_graph_async(self, config: RunnableConfig = None) -> CompiledStateGraph:
        """异步获取编译后的图"""
        return await self.build_graph_async(config)


    def get_compiled_graph(self) -> CompiledStateGraph:
        """获取编译后的图像，单例模式"""
        if self._compiled_graph is None:
            self._compiled_graph = self.build_graph()
        return self._compiled_graph


    def invoke(self, input: Dict[str, str], config: Dict[str, Any] = None) -> Dict[str,Any]:
        """同步调用Agent"""
        graph = self.get_compiled_graph()
        return graph.invoke(input, config)

    def stream(self, input: Dict[str, str], config: Dict[str, Any] = None):
        """流式调用"""
        graph = self.get_compiled_graph()
        return graph.stream(input, config)


    async def ainvoke(self, input: Dict[str, str], config: Dict[str, Any] = None) -> Dict[str,Any]:
        """异步调用"""
        graph = await self.get_compiled_graph_async(config)
        return await graph.ainvoke(input, config)

    async def astream(self, input: Dict[str, str], config: Dict[str, Any] = None):
        """异步流式调用"""
        graph = await self.get_compiled_graph_async(config)
        return await graph.astream(input, config)



class SimpleAgent(BaseAgent):
    """简单的ReAct Agent基类"""
    def __init__(self,
                 id: int,
                 agent_name: str,
                 tools: List,
                 model_name: str = "default",
                 system_prompt_template: Optional[Prompt] = None,
                 checkpointer:Optional[BaseCheckpointSaver] = None,
                 tool_manager:Optional[ToolManager] = None):
        super().__init__(checkpointer, tool_manager)
        self.id = id
        self.agent_name = agent_name
        self.model_name = model_name
        self.static_tools = tools or []
        self.system_prompt_template:Optional[Prompt] = system_prompt_template

    def getId(self)-> int:
        return self.id

    def get_info(self) -> AgentInfo:
        return AgentInfo(
            id=self.id,
            name=self.agent_name,
            description=f"Simple ReAct Agent:{self.agent_name}"
        )

    def build_graph(self) -> CompiledStateGraph:
        """构建ReAct agent图"""
        model = model_manager.get_model_by_name(self.model_name)
        from langgraph.prebuilt import create_react_agent
        graph = create_react_agent(name=self.agent_name,
                                   model=model,
                                   tools=self.static_tools,
                                   prompt=self.system_prompt_template,
                                   checkpointer=self.checkpointer)
        return graph
