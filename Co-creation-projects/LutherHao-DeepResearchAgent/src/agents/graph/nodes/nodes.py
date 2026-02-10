import json
import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command

from src.agents.graph.nodes.model.types import State
from src.agents.llms.llm_manager import llm_manager
from src.agents.prompt.template import apply_prompt_template
from src.infrastructure.config.configuration import Configuration

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


def coordinate_node(
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