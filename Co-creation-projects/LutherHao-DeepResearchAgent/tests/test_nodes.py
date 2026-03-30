"""
Tests for graph nodes (src/agents/graph/nodes/nodes.py).

All LLM calls are replaced by sandbox mock objects; no real API calls.
Search tools are also mocked. Each test asserts:
  - Correct routing (Command.goto)
  - Correct state updates (Command.update)
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from tests.sandbox import sandbox
from src.agents.graph.nodes.model.plan_model import Plan, Step
from src.agents.graph.nodes.model.types import State
from src.agents.graph.nodes.nodes import (
    coordinator_node,
    background_investigation_node,
    planner_node,
    reporter_node,
)
from src.infrastructure.config.configuration import Configuration


# ── Helpers ───────────────────────────────────────────────────────────────────

def _base_state(**extra) -> dict:
    return {
        "messages": [HumanMessage(content="AI市场分析")],
        "observations": [],
        "plan_iterations": 0,
        "current_plan": None,
        "final_report": "",
        "enable_background_investigation": True,
        "background_investigation_results": None,
        **extra,
    }


_BASE_CONFIG = {"configurable": {"thread_id": "test", "max_plan_iterations": 1, "max_step_num": 3}}


# ── coordinator_node ──────────────────────────────────────────────────────────

class TestCoordinatorNode:
    def test_no_tool_call_goes_to_end(self, sb):
        mock_model = sandbox.make_mock_llm(tool_calls=[])
        with patch("src.agents.graph.nodes.nodes.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            result = coordinator_node(_base_state(), _BASE_CONFIG)
        sandbox.assert_true(sb, isinstance(result, Command), "must return Command")
        sandbox.assert_equal(sb, result.goto, "__end__")

    def test_handoff_tool_call_goes_to_planner(self, sb):
        tool_call = {"name": "handoff_to_planner", "args": {}, "id": "tc1"}
        mock_model = sandbox.make_mock_llm(tool_calls=[tool_call])
        state = _base_state(enable_background_investigation=False)
        with patch("src.agents.graph.nodes.nodes.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            result = coordinator_node(state, _BASE_CONFIG)
        sandbox.assert_equal(sb, result.goto, "planner")

    def test_handoff_with_background_investigation_enabled(self, sb):
        tool_call = {"name": "handoff_to_planner", "args": {}, "id": "tc1"}
        mock_model = sandbox.make_mock_llm(tool_calls=[tool_call])
        state = _base_state(enable_background_investigation=True)
        with patch("src.agents.graph.nodes.nodes.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            result = coordinator_node(state, _BASE_CONFIG)
        sandbox.assert_equal(sb, result.goto, "background_investigation")


# ── background_investigation_node ─────────────────────────────────────────────

class TestBackgroundInvestigationNode:
    def test_returns_background_results(self, sb):
        mock_search = sandbox.make_mock_search([
            {"title": "AI Report", "content": "Deep analysis..."}
        ])
        state = _base_state()
        with patch("src.agents.graph.nodes.nodes.LoggedTavilySearch", return_value=mock_search):
            with patch("src.agents.graph.nodes.nodes.SEARCH_ENGINE", "tavily"):
                result = background_investigation_node(state, _BASE_CONFIG)
        sandbox.assert_in(sb, "background_investigation_results", result)
        sandbox.assert_true(sb, len(result["background_investigation_results"]) > 0, "should have content")

    def test_empty_search_results_handled(self, sb):
        mock_search = sandbox.make_mock_search([])
        state = _base_state()
        with patch("src.agents.graph.nodes.nodes.LoggedTavilySearch", return_value=mock_search):
            with patch("src.agents.graph.nodes.nodes.SEARCH_ENGINE", "tavily"):
                result = background_investigation_node(state, _BASE_CONFIG)
        sandbox.assert_in(sb, "background_investigation_results", result)


# ── planner_node ──────────────────────────────────────────────────────────────

class TestPlannerNode:
    def _make_plan_model(self):
        return Plan(
            has_enough_context=True,
            thought="Analyze the AI market",
            title="AI Market Analysis",
            steps=[
                Step(need_search=True, title="Research trends", description="Find data", step_type="research"),
                Step(need_search=False, title="Write report", description="Summarize", step_type="report"),
            ],
        )

    def test_generates_plan_and_routes_to_research_team(self, sb):
        plan = self._make_plan_model()
        mock_model = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = plan
        mock_model.with_structured_output.return_value = mock_structured

        state = _base_state()
        with patch("src.agents.graph.nodes.nodes.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            result = planner_node(state, _BASE_CONFIG)

        sandbox.assert_true(sb, isinstance(result, Command), "must return Command")
        sandbox.assert_equal(sb, result.goto, "research_team")
        sandbox.assert_not_none(sb, result.update.get("current_plan"))

    def test_exceeds_max_iterations_routes_to_reporter(self, sb):
        plan = self._make_plan_model()
        mock_model = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = plan
        mock_model.with_structured_output.return_value = mock_structured

        # Set plan_iterations >= max_plan_iterations (both are 1)
        state = _base_state(plan_iterations=1)
        with patch("src.agents.graph.nodes.nodes.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            result = planner_node(state, _BASE_CONFIG)
        sandbox.assert_equal(sb, result.goto, "reporter")


# ── reporter_node ─────────────────────────────────────────────────────────────

class TestReporterNode:
    """reporter_node was previously incomplete (no LLM call, no return)."""

    def test_invokes_llm_and_returns_final_report(self, sb):
        mock_model = sandbox.make_mock_llm(response_content="# 市场分析报告\n\n## 摘要\n\n详细内容...")
        plan = Plan(
            has_enough_context=True,
            thought="分析AI市场",
            title="2025 AI市场报告",
            steps=[],
        )
        state = _base_state(current_plan=plan, observations=["观察结果1", "观察结果2"])

        with patch("src.agents.graph.nodes.nodes.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            result = reporter_node(state, _BASE_CONFIG)

        sandbox.assert_not_none(sb, result)
        sandbox.assert_in(sb, "final_report", result)
        sandbox.assert_equal(sb, result["final_report"], "# 市场分析报告\n\n## 摘要\n\n详细内容...")
        sandbox.assert_in(sb, "messages", result)
        sandbox.assert_equal(sb, result["messages"][0].name, "reporter")

    def test_reporter_without_plan(self, sb):
        mock_model = sandbox.make_mock_llm(response_content="No plan report")
        state = _base_state(current_plan=None, observations=[])

        with patch("src.agents.graph.nodes.nodes.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            result = reporter_node(state, _BASE_CONFIG)

        sandbox.assert_equal(sb, result["final_report"], "No plan report")

    def test_reporter_appends_observations(self, sb):
        """_add_system_prompts injects observations into the message list."""
        mock_model = sandbox.make_mock_llm(response_content="Report with obs")
        plan = Plan(has_enough_context=True, thought="t", title="T", steps=[])
        state = _base_state(current_plan=plan, observations=["obs1", "obs2", "obs3"])

        with patch("src.agents.graph.nodes.nodes.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            result = reporter_node(state, _BASE_CONFIG)
            # Verify model.invoke was called with at least some messages
            call_args = mock_model.invoke.call_args
            messages_arg = call_args[0][0]
            sandbox.assert_true(sb, len(messages_arg) > 1, "invoke should receive multiple messages")
