from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from src.agents.base.base_agent import MultiAgent
from src.agents.model.agent_info import AgentInfo
from src.agents.registry.instance_registry import registry


@registry("deep_research_agent")
class DeepResearchAgent(MultiAgent):
    """
    Deep Research 工作流 Agent
    """

    def __init__(self,
                 checkpointer: Optional[BaseCheckpointSaver] = None):
        """初始化 Agent"""
        self.checkpointer = checkpointer if checkpointer else InMemorySaver()
        super().__init__()


    def build_workflow(self) -> CompiledStateGraph:
        """构建工作流"""
        return build_graph_with_checkpoint(
            checkpointer=self.checkpointer,
        )

    @classmethod
    def get_info(cls) -> AgentInfo:
        """获取 Agent 信息"""
        return AgentInfo(
            id="deep_research_agent",
            name="Deep Research Agent",
            description="支持多步骤研究,规划,报告生成的通用工作流Agent"
        )