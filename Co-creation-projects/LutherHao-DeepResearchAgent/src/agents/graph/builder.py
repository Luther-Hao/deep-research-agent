from joblib import Memory
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Checkpointer

from src.agents.graph.nodes.model.types import State

from src.agents.graph.nodes.nodes import (
    coordinator_node,
    background_investigation_node
)

def _build_base_graph():
    """
    基础工作流

    流程
    START -> coordinator -> [background_investigation] -> planner -> human_feedback -> research_team -> reporter -> END

    research_team 根据计划步骤类型路由
    - researcher
    - coder
    - excel_analyser
    - reporter
    """

    builder = StateGraph(State)

    # 构建图像
    builder.add_node("coordinator",coordinator_node)
    builder.add_node("background_investigation",background_investigation_node)
    builder.add_node("planner",planner_node)
    builder.add_node("human_feedback",human_feedback_node)
    builder.add_node("dynamic_assistant", dynamic_assistant_node)


    builder.add_node("research_team",research_team_node)

    builder.add_node("researcher",researcher_node)
    builder.add_node("coder",coder_node)
    builder.add_node("excel_analyser",excel_anaylser_node)
    builder.add_node("reporter",reporter_node)

    # add edge
    builder.add_edge(START, "coordinator")
    builder.add_edge("background_investigation", "planner")

    builder.add_edge("researcher", "research_team")
    builder.add_edge("coder", "research_team")
    builder.add_edge("excel_analyser", "research_team")

    builder.add_edge("dynamic_assistant", "research_team")

    builder.add_conditional_edges(
        "research_team",
        get_next_research_step_node
    )
    return builder



def build_graph_with_checkpointer(checkpoint : Checkpointer):
    main_builder = StateGraph(State)
    base_graph = _build_base_graph()

    # 将基本链路逻辑添加到主图当中
    main_builder.add_node("base_graph", base_graph.compile(checkpointer=checkpoint))

    # 添加路径
    main_builder.add_edge(START, "base_graph")
    main_builder.add_edge("base_graph", END)

    return main_builder.compile(checkpointer=checkpoint)


def build_graph():
    memory = MemorySaver()
    return build_graph_with_checkpointer(memory)

def get_graph_builder():
    memory = MemorySaver()
    return build_graph_with_checkpointer(memory)


