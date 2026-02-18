import logging

from langgraph.prebuilt import create_react_agent

from src.agents.graph.builder import build_graph
from src.agents.llms.llm_manager import llm_manager
from src.agents.prompt.template import apply_prompt_template

logger = logging.getLogger(__name__)


graph = build_graph()

async def run_async(user_input: str,
                    max_plan_iterations: int = 1,
                    max_step_num: int = 3,
                    enable_background_investigation: bool = True,
                    enable_clarification: bool | None = None,
                    max_clarification_rounds: int | None = None,
                    initial_state: dict | None = None):
    if not user_input:
        raise ValueError("User input cannot be empty.")

    logger.info(f"Agent working start with user input: {user_input}")

    # 捕获状态图是否正常
    if initial_state is None:
        initial_state = {
            "messages":[{
                "role":"user",
                "content":user_input,
            }],
            "enable_background_investigation": enable_background_investigation,
            "enable_clarification": enable_clarification,
            "research_topic": user_input,
            "clarification_topic": user_input
        }

        if enable_clarification is not None:
            initial_state["enable_clarification"] = enable_clarification

        if max_clarification_rounds is not None:
            initial_state["max_clarification_rounds"] = max_clarification_rounds


    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "mcp_settings": {
                "servers":{
                    "mcp-github-trending": {
                        "transport": "stdio",
                        "command": "uvx",
                        "args":["mcp-github-trending"],
                        "enabled_tools": ["get_github_trending_repositories"],
                        "add_to_agents":["researcher"],
                    }
                }
            },
        },
    }
    last_message_cnt = 0
    final_state = None
    async for s in graph.astream(
        input=initial_state,
        config=config,
        stream_mode="values"
    ):
        try:
            final_state = s
            if isinstance(final_state, dict) and "messages" in s:
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
            print(f"Error processing stream output: {str(e)}")

    logger.info(f"Agent working end with user input: {user_input}")


def create_agent_dynamic(agent_name: str, agent_type:str, tools:list, prompt_template:str,model_name:str):
    model = llm_manager.get_model_by_name(model_name)
    return create_react_agent(
        name=agent_name,
        model=model,
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state),
    )

