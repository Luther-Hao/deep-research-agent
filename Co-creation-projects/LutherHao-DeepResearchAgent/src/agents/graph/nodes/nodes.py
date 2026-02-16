import json
import logging
from json import JSONDecodeError
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command

from src.agents.graph.nodes.model.plan_model import Plan
from src.agents.graph.nodes.model.types import State
from src.agents.llms.llm_manager import llm_manager
from src.agents.prompt.template import apply_prompt_template
from src.agents.tool.tools.search_tool import LoggedTavilySearch, get_web_search_tool
from src.agents.utils.json_utils import repair_json_output
from src.infrastructure.config.configuration import Configuration
from src.infrastructure.config.search_tools_config import SEARCH_ENGINE, SearchEngine

logger = logging.getLogger(__name__)


def _get_available_tools_info_for_prompt(configurable):
    """获取可用的工具放到提示词当中"""
    tools_info = []

    if configurable.mcp_settings and configurable.mcp_settings.get("servers"):
        tools_info.append("\nMCP tools:")
        mcp_tools_info = {}
        for server_name, server_config in configurable.mcp_settings.get("servers",{}).items():
            enable_tools = server_config.get("enable_tools", [])
            if enable_tools and isinstance(enable_tools[0], dict):
                mcp_tools_info[server_name] = enable_tools
            else:
                mcp_tools_info[server_name] = [{"name": tool_name} for tool_name in enable_tools]

    if mcp_tools_info:
        tools_info.append(json.dumps(mcp_tools_info, ensure_ascii=False, indent=2))

    return "\n".join(tools_info)

@tool
def handoff_to_planner():
    return


def coordinator_node(
        state: State,
        config: RunnableConfig
)-> Command[Literal["planner", "background_investigation","__end__"]]:
    """协调器节点"""
    logger.info("coordinate_node is running")
    configurable = Configuration.from_runnable_config(config)

    tool_info = _get_available_tools_info_for_prompt(configurable)
    state_with_tools_info = {**state,"tools_info":tool_info} if tool_info else state

    messages = apply_prompt_template("coordinator", state_with_tools_info)
    model = llm_manager.get_model_by_name(configurable.model).bind_tools([handoff_to_planner])
    response = model.invoke(messages)

    goto = "__end__"

    if len(response.tool_calls) > 0:
        goto = "planner"
        if state.get("enable_background_investigation"):
            goto = "background_investigation"
        try:
            for tool_call in response.tool_calls:
                if tool_call.get("name", "") == "handoff_to_excelAnalyser":
                    goto = "excel_analyser"
                if tool_call.get("name", "") != "handoff_to_planner":
                    continue
        except Exception as e:
            logger.error(f"error for tool call:{e}")
    else:
        logger.info("coordinate_node is done")
    return Command(
        goto=goto
    )


def background_investigation_node(
        state: State,
        config: RunnableConfig
):
    logger.info("background_investigation_node is running")
    configurable = Configuration.from_runnable_config(config)
    query = state["messages"][-1].content

    if SEARCH_ENGINE == SearchEngine.TAVILY.value:
        searched_content = LoggedTavilySearch(
            max_results=configurable.max_search_result,
        ).invoke(query)
        if isinstance(searched_content, list):
            background_investigation_results = [
                f"## {elem['title']}\n\n{elem['content']}" for elem in searched_content
            ]
            return {
                "background_investigation_results": "\n\n".join(background_investigation_results)
            }
        else:
            logger.error(
                f"Tavily search for {searched_content} is invalid"
            )
    else:
        background_investigation_results = get_web_search_tool(
            configurable.max_search_result
        ).invoke(query)
    return {
        "background_investigation_results": json.dumps(
            background_investigation_results, ensure_ascii=False
        )
    }

def planner_node(
        state: State,
        config: RunnableConfig
) -> Command[Literal["human_feedback", "research_team","reporter"]]:
    """生成完整的计划"""
    logger.info("planner_node is running")

    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0

    tool_info = _get_available_tools_info_for_prompt(configurable)
    state_with_tools_info = {**state,"tools_info":tool_info} if tool_info else state

    messages = apply_prompt_template("planner", state_with_tools_info, configurable)

    if (
        plan_iterations == 0
        and state.get("enable_background_investigation")
        and state.get("background_investigation_results")
    ):
        messages += [
            {
                "role": "user",
                "content": (
                   "用户查询的背景调查结果：\n" + state["background_investigation_results"] + "\n"
                )
            }
        ]

    llm = llm_manager.get_model_by_name(configurable.model).with_structured_output(
        Plan,
        method="json_mode"
    )

    if plan_iterations >= configurable.max_plan_iterations:
        return Command(
            goto="reporter"
        )

    full_response = ""
    response = llm.invoke(messages)
    full_response = response.model_dump_json(indent=4, exclude_none=True)

    logger.info(f"planner node is done, response is {full_response}")

    try:
        curr_plan = json.loads(repair_json_output(full_response))
    except JSONDecodeError as e:
        logger.error("plan is invalid")
        if plan_iterations > 0:
            return Command(
                goto="reporter"
            )
        else:
            return Command(
                goto="__end__"
            )


    if curr_plan.get("has_enough_context"):
        logger.info("This plan is enough")
        new_plan = Plan.model_validate(curr_plan)

        return Command(
            update={
                "message":[AIMessage(content=full_response, name="planner")],
                "current_plan":new_plan
            },
            goto="human_feedback"
        )



