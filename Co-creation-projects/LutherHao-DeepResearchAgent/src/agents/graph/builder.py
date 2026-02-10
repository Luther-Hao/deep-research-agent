from langgraph.graph import StateGraph
from langgraph.types import Checkpointer

from src.agents.graph.nodes.model.types import State


def _build_base_graph():
    """
    基础工作流

    流程
    START -> coordinator -> [background_investigation] -> planner -> human_feedback -> research_team ->
    END

    research_team 根据计划步骤类型路由
    - researcher
    - coder
    - excel_analyser
    - reporter
    """

    builder = StateGraph(State)

    # 构建图像
    builder.add_node(coordinator_node)

    pass


def _build_analyser_graph():
    pass


def build_graph_with_checkpointer(checkpoint : Checkpointer):
    """构建包含两个子图的工作流"""
    main_builder = StateGraph(State)

    # 两个子图
    base_graph = _build_base_graph()
    report_graph = _build_analyser_graph()

