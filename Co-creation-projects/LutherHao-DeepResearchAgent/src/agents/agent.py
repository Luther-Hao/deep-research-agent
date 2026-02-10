import logging

logger = logging.getLogger(__name__)



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


