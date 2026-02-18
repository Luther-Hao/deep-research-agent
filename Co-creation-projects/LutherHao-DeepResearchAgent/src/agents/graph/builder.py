from joblib import Memory
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Checkpointer

from src.agents.graph.nodes.model.plan_model import StepType, STEP_TYPE_TO_NODE_MAP
from src.agents.graph.nodes.model.types import State

from src.agents.graph.nodes.nodes import (
    coordinator_node,
    background_investigation_node, planner_node, human_feedback_node, research_team_node, researcher_node, coder_node,
    reporter_node
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


    builder.add_node("research_team",research_team_node)

    builder.add_node("researcher",researcher_node)
    builder.add_node("coder",coder_node)
    builder.add_node("reporter",reporter_node)

    # add edge
    builder.add_edge(START, "coordinator")
    builder.add_edge("background_investigation", "planner")

    builder.add_edge("researcher", "research_team")
    builder.add_edge("coder", "research_team")

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


def get_next_research_step_node(state: State) -> str:
    """
    获取当前计划的研究步骤类型，并路由到对应的执行节点

    研究步骤类型如下：
    - research:研究员节点
    - processin: 编码员节点
    :param state:
    :return: 下一个执行节点的名称或者 REPORTER
    """

    current_plan = state.get("current_plan")

    if not current_plan or not current_plan.steps:
        return "planner"

    current_step = current_plan.get_next_unexecuted_research_team_step()

    if not current_step:
        return "reporter"

    step_type = current_step.step_type

    try:
        step_type_enum = StepType(step_type)
        if step_type_enum in STEP_TYPE_TO_NODE_MAP:
            return STEP_TYPE_TO_NODE_MAP[step_type_enum].value
    except ValueError:
        pass

    return "reporter"






def build_graph():
    memory = MemorySaver()
    return build_graph_with_checkpointer(memory)

def get_graph_builder():
    memory = MemorySaver()
    return build_graph_with_checkpointer(memory)


