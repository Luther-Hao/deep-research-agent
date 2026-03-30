"""
Tests for src/agents/graph/builder.py

Covers:
  - get_next_research_step_node routing logic
  - build_graph returns a compiled graph
"""

import pytest
from tests.sandbox import sandbox
from src.agents.graph.nodes.model.plan_model import Plan, Step, StepType
from src.agents.graph.nodes.model.types import State
from src.agents.graph.builder import get_next_research_step_node
from langchain_core.messages import HumanMessage


def _state_with_plan(*step_types: str, done_indices: list[int] | None = None) -> dict:
    steps = [
        Step(need_search=True, title=f"Step {i}", description="d", step_type=st)
        for i, st in enumerate(step_types)
    ]
    if done_indices:
        for idx in done_indices:
            steps[idx].execution_res = f"result_{idx}"
    plan = Plan(has_enough_context=True, thought="t", title="T", steps=steps)
    return {
        "messages": [HumanMessage(content="test")],
        "current_plan": plan,
        "observations": [],
        "plan_iterations": 0,
        "final_report": "",
        "enable_background_investigation": True,
        "background_investigation_results": None,
    }


class TestGetNextResearchStepNode:
    def test_no_plan_returns_planner(self, sb):
        state = {
            "messages": [],
            "current_plan": None,
            "observations": [],
        }
        result = get_next_research_step_node(state)
        sandbox.assert_equal(sb, result, "planner")

    def test_empty_steps_returns_planner(self, sb):
        plan = Plan(has_enough_context=True, thought="t", title="T", steps=[])
        state = {"messages": [], "current_plan": plan, "observations": []}
        result = get_next_research_step_node(state)
        sandbox.assert_equal(sb, result, "planner")

    def test_routes_to_researcher(self, sb):
        state = _state_with_plan("research")
        result = get_next_research_step_node(state)
        sandbox.assert_equal(sb, result, "researcher")

    def test_routes_to_coder(self, sb):
        state = _state_with_plan("processing")
        result = get_next_research_step_node(state)
        sandbox.assert_equal(sb, result, "coder")

    def test_all_done_returns_reporter(self, sb):
        state = _state_with_plan("research", done_indices=[0])
        result = get_next_research_step_node(state)
        sandbox.assert_equal(sb, result, "reporter")

    def test_unknown_step_type_returns_reporter(self, sb):
        state = _state_with_plan("unknown_type")
        result = get_next_research_step_node(state)
        sandbox.assert_equal(sb, result, "reporter")

    def test_sequential_routing(self, sb):
        """research done, processing next → coder."""
        state = _state_with_plan("research", "processing", done_indices=[0])
        result = get_next_research_step_node(state)
        sandbox.assert_equal(sb, result, "coder")


class TestBuildGraph:
    def test_build_graph_returns_compiled(self, sb):
        """build_graph() must return a runnable CompiledGraph."""
        from src.agents.graph.builder import build_graph
        g = build_graph()
        sandbox.assert_not_none(sb, g)
        # LangGraph compiled graphs have .invoke / .astream methods
        sandbox.assert_true(sb, hasattr(g, "astream"), "graph must have .astream")
        sandbox.assert_true(sb, hasattr(g, "invoke"), "graph must have .invoke")
