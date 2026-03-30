import logging
from typing import AsyncIterator

from langgraph.prebuilt import create_react_agent  # noqa: LangGraph v1 deprecation

from src.agents.graph.builder import build_graph
from src.agents.llms.llm_manager import llm_manager
from src.agents.prompt.template import apply_prompt_template

logger = logging.getLogger(__name__)


graph = build_graph()

DEFAULT_MCP_SETTINGS = {
    "servers": {
        "mcp-github-trending": {
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-github-trending"],
            "enabled_tools": ["get_github_trending_repositories"],
            "add_to_agents": ["researcher"],
        }
    }
}


def _build_config(
    max_plan_iterations: int,
    max_step_num: int,
    thread_id: str = "default",
    mcp_settings: dict = None,
) -> dict:
    return {
        "configurable": {
            "thread_id": thread_id,
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "mcp_settings": mcp_settings or DEFAULT_MCP_SETTINGS,
        },
    }


def _build_initial_state(
    user_input: str,
    enable_background_investigation: bool,
    enable_clarification: bool | None,
    max_clarification_rounds: int | None,
) -> dict:
    state: dict = {
        "messages": [{"role": "user", "content": user_input}],
        "enable_background_investigation": enable_background_investigation,
        "research_topic": user_input,
        "clarification_topic": user_input,
    }
    if enable_clarification is not None:
        state["enable_clarification"] = enable_clarification
    if max_clarification_rounds is not None:
        state["max_clarification_rounds"] = max_clarification_rounds
    return state


async def run_async(
    user_input: str,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
    enable_clarification: bool | None = None,
    max_clarification_rounds: int | None = None,
    initial_state: dict | None = None,
):
    if not user_input:
        raise ValueError("User input cannot be empty.")

    logger.info(f"Agent working start with user input: {user_input}")

    if initial_state is None:
        initial_state = _build_initial_state(
            user_input, enable_background_investigation, enable_clarification, max_clarification_rounds
        )

    config = _build_config(max_plan_iterations, max_step_num)
    last_message_cnt = 0
    async for s in graph.astream(input=initial_state, config=config, stream_mode="values"):
        try:
            if isinstance(s, dict) and "messages" in s:
                if len(s["messages"]) <= last_message_cnt:
                    continue
                last_message_cnt = len(s["messages"])
                message = s["messages"][-1]
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()
            else:
                print(f"Output: {s}")
        except Exception as e:
            logger.error(f"Error processing stream output: {e}")

    logger.info(f"Agent working end with user input: {user_input}")


async def run_stream(
    user_input: str,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
) -> AsyncIterator[dict]:
    """Yield structured events for SSE streaming to the frontend."""
    if not user_input:
        raise ValueError("User input cannot be empty.")

    logger.info(f"[stream] start: {user_input}")

    initial_state = _build_initial_state(user_input, enable_background_investigation, None, None)
    config = _build_config(max_plan_iterations, max_step_num)

    last_message_cnt = 0
    final_report = ""

    async for s in graph.astream(input=initial_state, config=config, stream_mode="values"):
        try:
            if not isinstance(s, dict):
                continue

            if "messages" in s:
                messages = s["messages"]
                if len(messages) > last_message_cnt:
                    last_message_cnt = len(messages)
                    msg = messages[-1]
                    role = getattr(msg, "name", None) or getattr(msg, "type", "assistant")
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    if content:
                        yield {"type": "message", "role": role, "content": content}

            if s.get("final_report"):
                final_report = s["final_report"]

        except Exception as e:
            logger.error(f"[stream] error: {e}")
            yield {"type": "error", "message": str(e)}

    if final_report:
        yield {"type": "final_report", "content": final_report}

    yield {"type": "done"}
    logger.info("[stream] done")


def create_agent_dynamic(agent_name: str, agent_type: str, tools: list, prompt_template: str, model_name: str):
    model = llm_manager.get_model_by_name(model_name)
    return create_react_agent(
        name=agent_name,
        model=model,
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state),
    )
