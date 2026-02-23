import json
import logging
import os
from json import JSONDecodeError
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command, interrupt

from src.agents.graph.nodes.model.plan_model import Plan
from src.agents.graph.nodes.model.types import State
from src.agents.llms.llm_manager import llm_manager
from src.agents.prompt.template import apply_prompt_template
from src.agents.tool.tools.impl.file_loader_tool import FileLoader
from src.agents.tool.tools.search_tool import LoggedTavilySearch, get_web_search_tool
from src.agents.utils.data_utils import safe_truncate
from src.agents.utils.json_utils import repair_json_output
from src.infrastructure.config.configuration import Configuration
from src.infrastructure.config.search_tools_config import SEARCH_ENGINE, SearchEngine
from src.infrastructure.mcp.config_utils import extract_mcp_server_config, normalize_enabled_tools

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
    """直接通向计划者，无需做任何处理"""
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
            goto="research_team"
        )


def human_feedback_node(
        state,
        config: RunnableConfig
) -> Command[Literal["planner", "research_team","__end__"]]:
    logger.info("human_feedback_node is running")
    raw_plan = state.get("current_plan","")
    current_plan = raw_plan

    if hasattr(raw_plan, "model_dump_json"):
        current_plan = raw_plan.model_dump_json()
    elif not isinstance(raw_plan, str):
        current_plan = str(raw_plan)

    auto_accepted_plan = state.get("auto_accepted_plan",False)
    if not auto_accepted_plan:
        feedback = interrupt("Please Review the Plan:\n"
                   "- Enter [ACCEPTED] to approve the plan\n"
                   "- Enter [EDIT_PLAN] + your new plan to modify\n"
                   "- Empty input will return to planner")

        if not feedback:
            logger.warning(f"Received empty or None feedback: {feedback}. Return to Planner")
            return Command(
                goto="planner"
            )

        feedback_normalized = str(feedback).strip().upper()

        if feedback_normalized.startswith("[EDIT_PLAN]"):
            return Command(
                update={
                    "messages":[
                        HumanMessage(content=feedback,name="feedback"),
                    ]
                },
                goto="planner"
            )
        elif feedback_normalized.startswith("[ACCEPTED]"):
            logger.info("Plan is accepted")
        else:
            raise TypeError(f"Interrupt value of {feedback} is not supported")

    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    goto = "research_team"

    try:
        current_plan = repair_json_output(current_plan)
        plan_iterations += 1
        new_plan = json.loads(current_plan)
    except JSONDecodeError as e:
        logger.error("plan is invalid")
        if plan_iterations > 0:
            return Command(
                goto="research_team"
            )
        else:
            return Command(
                goto="__end__"
            )

    return Command(
        update={
            "current_plan":Plan.model_validate(new_plan),
            "plan_iterations":plan_iterations,
        },
        goto=goto
    )


def research_team_node(state: State):
    logger.info("research_team node is running")
    pass


def _build_agent_input(
        message:list,
        current_step: "Step" = None,
        completed_steps: list = None,
        include_completed_findings:bool = False
):
    """
    构建Agent输入函数
    :param message:
    :param current_step:
    :param completed_steps:
    :param include_completed_findings:是否包含已经完成的步骤信息
    :return:
    """
    agent_input = {"messages":[]}

    if include_completed_findings and completed_steps:
        completed_steps_info = "# Existing Research Findings\n\n"
        for i, step in enumerate(completed_steps):
            completed_steps_info += f"## Existing Finding {i + 1}： {step.title}\n\n"
            completed_steps_info += f"<finding>\n{step.execution_res}\n</finding>\n\n"
    else:
        completed_steps_info = ""


    if current_step:
        content = f"{completed_steps_info}# Current Task\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}"
    else:
        content = completed_steps_info

    agent_input["messages"].append(HumanMessage(content=content))
    return agent_input



def _add_system_prompts(message:list, prompt_type:str, **kwargs) -> None:
    """添加系统提示词"""
    if prompt_type == "researcher":
        message.append(
            HumanMessage(
                content="重要：不要在文本中包含内联引用。相反，请在末尾的参考文献部分中跟踪所有来源，使用链接参考格式，每个引用之间包含一个空行以提高可读性。使用以下格式：\n-[来源标题](URL)\n\n-[另一个来源](URL)",
                name="system"
            )
        )

    elif prompt_type == "reporter":
        message.append(
            HumanMessage(
                content="重要：按照提示词中的格式组织报告。记住要包含：\n\n1. 关键要点 - 最重要发现的项目列表\n2. 概述 - 对主题的简要介绍\n3. 详细分析 - 组织成逻辑部分\n4. 调查说明（可选）- 用于更全面的报告\n5. 关键引用 - 在末尾列出所有参考文献\n\n对于引用，不要在文本中包含内联引用。相反，将所有引用放在末尾的关键引用部分中，使用格式：`- [来源标题](URL)`。每个引用之间包含一个空行以提高可读性。\n\n优先使用 Markdown 表格进行数据呈现和比较。在呈现比较数据、统计数据、功能或选项时使用表格。使用清晰的标题和对齐的列来组织表格。示例表格格式：\n\n| 功能 | 描述 | 优点 | 缺点 |\n|------|------|------|------|\n| 功能 1 | 描述 1 | 优点 1 | 缺点 1 |\n| 功能 2 | 描述 2 | 优点 2 | 缺点 2 |",
                name="system"
            )
        )

        observations = kwargs.get("observations", [])
        for observation in observations:
            message.append(
                HumanMessage(
                    content=f"以下是研究任务的一些观察结果：\n\n{observation}",
                    name="observation"
                )
            )



async def _run_research_team_step_with_agent(
        state: State,
        agent,
        agent_name: str) -> Command[Literal["research_team"]]:
    """"""
    current_plan = state.get("current_plan")
    observations = state.get("observations",[])

    current_step = current_plan.get_next_unexecuted_research_team_step()
    completed_steps = current_plan.get_completed_steps()

    if not current_step:
        logger.warning(f"No steps completed for {agent_name}")
        return Command(
            goto="research_team"
        )

    logger.info(f"Agent is running:{current_step.title},agent:{agent_name}")

    agent_input = _build_agent_input(
        message=state.get("message",[]),
        current_step=current_step,
        completed_steps=completed_steps,
        include_completed_findings=False
    )

    _add_system_prompts(
        agent_input["messages"],
        agent_name,
    )


    default_recursion_limit = 5
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
        limit = int(env_value_str)

        if limit > 0:
            recursion_limit = limit
            logger.info(f"Recursion limit set to {limit}")
        else:
            logger.warning(f"Recursion limit set to {default_recursion_limit}")
            recursion_limit = default_recursion_limit
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        recursion_limit = default_recursion_limit

    logger.info(f"Agent input is: {safe_truncate(agent_input)}")


    try:
        result = await agent.ainvoke(
            input=agent_input,
            config={"recursion_limit": recursion_limit},
        )

        response_content = result["message"][-1].content
        logger.info(f"Step '{current_step.title}' completed successfully")

        return Command(
            update={
                "messages":[
                    HumanMessage(content=response_content,name=agent_name),
                ],
                "observations":observations + [response_content],
            },
            goto="research_team"
        )
    except Exception as e:
        current_step.execution_res = str(e)
        logger.error(f"Step '{current_step.title}' failed")
        return Command(
            update={
                "messages":[
                    HumanMessage(content=f"{str(e)}",name="agent.ainvoke"),
                ]
            },
            goto="research_team"
        )




async def _execute_research_team_step_with_tools(
        state:State,
        config:RunnableConfig,
        agent_type:str,
        tools:list):
    """执行研究团队步骤，并且根据配置动态加载工具

    用于处理研究团队节点的通用逻辑

    """
    configurable = Configuration.from_runnable_config(config)
    mcp_servers={}
    enabled_tools={}
    model = configurable.model

    if configurable.mcp_settings:
        for server_name, server_config in configurable.mcp_settings["servers"].items():
            if(
                server_config["enable_tools"]
                and agent_type in ("researcher", "coder")
            ):
                mcp_servers[server_name] = extract_mcp_server_config(server_config)

                # 处理工具列表, 使用统一的标准化函数
                enabled_tools_list = server_config["enabled_tools"]
                if enabled_tools_list:
                    normalized_tools = normalize_enabled_tools(enabled_tools_list)
                    for tool_name in normalized_tools:
                        enabled_tools[tool_name] = server_name

    from src.agents.agent import create_agent_dynamic
    if mcp_servers:
        client = MultiServerMCPClient(mcp_servers)
        loaded_tools = tools[:]
        for tool in await client.get_tools():
            if tool.name in enabled_tools:
                tool.description = (
                    f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                )
                loaded_tools.append(tool)


        agent = create_agent_dynamic(agent_type, agent_type, loaded_tools, agent_type, model)
        return await _run_research_team_step_with_agent(state, agent, agent_type)
    else:
        agent = create_agent_dynamic(agent_type, agent_type, tools, agent_type, model)
        return await _run_research_team_step_with_agent(state, agent, agent_type)


async def researcher_node(state: State,
                    config: RunnableConfig)-> Command[Literal["research_team"]]:
    logger.info("researcher_node is running")
    configurable = Configuration.from_runnable_config(config)
    searchTool = get_web_search_tool(configurable.max_search_result)
    tools = [searchTool]
    logger.info(f"Tools are {tools}")
    return await _execute_research_team_step_with_tools(
        state,
        config,
        "researcher",
        tools
    )


async def coder_node(
        state: State,
        config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """编码节点"""
    logger.info("coder_node is running")
    fileLoader = FileLoader(
        message=state.get("message",[])
    )
    return await _execute_research_team_step_with_tools(
        state,
        config,
        "coder",
        [fileLoader]
    )


def reporter_node(state: State,config: RunnableConfig):
    logger.info("reporter_node is running")
    current_plan = state.get("current_plan")
    messages = state.get("messages",[])
    messages.append(
        HumanMessage(
            f"# Research Requirements\n\n## Task\n\n{current_plan.title}\n\n## Description\n\n{current_plan.thought}",
        )
    )
    input = {
        "messages":messages
    }
    invoke_message = apply_prompt_template("reporter",input)
    observations = state.get("observations",[])

    _add_system_prompts(
        invoke_message,
        "reporter",
        observations=observations
    )






