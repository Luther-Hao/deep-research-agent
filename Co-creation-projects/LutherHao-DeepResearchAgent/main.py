# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Entry point script.
"""

import argparse
import asyncio

from InquirerPy import inquirer

from src.agents.agent import run_async


def ask(
    question,
    debug=False,
    max_plan_iterations=1,
    max_step_num=3,
    enable_background_investigation=True,
    enable_clarification=False,
    max_clarification_rounds=None,
    locale=None,
):

    asyncio.run(
        run_async(
            user_input=question,
            max_plan_iterations=max_plan_iterations,
            max_step_num=max_step_num,
            enable_background_investigation=enable_background_investigation,
            enable_clarification=enable_clarification,
            max_clarification_rounds=max_clarification_rounds
        )
    )


def main(
    debug=False,
    max_plan_iterations=1,
    max_step_num=3,
    enable_background_investigation=True,
    enable_clarification=False,
    max_clarification_rounds=None,
):
    # 初始化问题
    questions = BUILT_IN_QUESTIONS_ZH_CN

    ask_own_option = "[自定义问题]"

    # Select a question
    initial_question = inquirer.select(
        message="您想了解什么?",
        choices=[ask_own_option] + questions,
    ).execute()

    if initial_question == ask_own_option:
        initial_question = inquirer.text(
            message="您想了解什么?",
        ).execute()

    # Pass all parameters to ask function
    ask(
        question=initial_question,
        debug=debug,
        max_plan_iterations=max_plan_iterations,
        max_step_num=max_step_num,
        enable_background_investigation=enable_background_investigation,
        enable_clarification=enable_clarification,
        max_clarification_rounds=max_clarification_rounds
    )


if __name__ == "__main__":
    # 命令行设置传入参数
    parser = argparse.ArgumentParser(description="运行Agent")
    # 添加位置参数用于接收命令行控制
    parser.add_argument("query", nargs="*", help="The query to process")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode with built-in questions",
    )
    parser.add_argument(
        "--max_plan_iterations",
        type=int,
        default=1,
        help="Maximum number of plan iterations (default: 1)",
    )
    parser.add_argument(
        "--max_step_num",
        type=int,
        default=3,
        help="Maximum number of steps in a plan (default: 3)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--no-background-investigation",
        action="store_false",
        dest="enable_background_investigation",
        help="Disable background investigation before planning",
    )
    parser.add_argument(
        "--enable-clarification",
        action="store_true",
        dest="enable_clarification",
        help="Enable multi-turn clarification for vague questions (default: disabled)",
    )
    parser.add_argument(
        "--max-clarification-rounds",
        type=int,
        dest="max_clarification_rounds",
        help="Maximum number of clarification rounds (default: 3)",
    )

    args = parser.parse_args()

    if args.interactive:
        # Pass command line arguments to main function
        main(
            debug=args.debug,
            max_plan_iterations=args.max_plan_iterations,
            max_step_num=args.max_step_num,
            enable_background_investigation=args.enable_background_investigation,
            enable_clarification=args.enable_clarification,
            max_clarification_rounds=args.max_clarification_rounds,
        )
    else:
        # Parse user input from command line arguments or user input
        if args.query:
            user_query = " ".join(args.query)
        else:
            # Loop until user provides non-empty input
            while True:
                user_query = input("Enter your query: ")
                if user_query is not None and user_query != "":
                    break

        # Run the agent workflow with the provided parameters
        ask(
            question=user_query,
            debug=args.debug,
            max_plan_iterations=args.max_plan_iterations,
            max_step_num=args.max_step_num,
            enable_background_investigation=args.enable_background_investigation,
            enable_clarification=args.enable_clarification,
            max_clarification_rounds=args.max_clarification_rounds,
        )