"""
Tests for src/agents/graph/nodes/model/plan_model.py

Covers:
  - Step validation
  - Plan validation and method correctness
  - StepType enum + STEP_TYPE_TO_NODE_MAP mapping
  - Bug fix: get_research_steps() compares step.step_type not the Step object itself
"""

import pytest
from tests.sandbox import sandbox
from src.agents.graph.nodes.model.plan_model import (
    Plan, Step, StepType, STEP_TYPE_TO_NODE_MAP,
)


# ── Step model ───────────────────────────────────────────────────────────────

class TestStep:
    def test_step_creation_minimal(self, sb):
        step = Step(need_search=True, title="Find market data", description="Search for data", step_type="research")
        sandbox.assert_equal(sb, step.title, "Find market data")
        sandbox.assert_equal(sb, step.step_type, "research")
        sandbox.assert_equal(sb, step.execution_res, None)

    def test_step_execution_res(self, sb):
        step = Step(need_search=False, title="T", description="D", step_type="processing", execution_res="done")
        sandbox.assert_equal(sb, step.execution_res, "done")

    def test_step_type_values(self, sb):
        sandbox.assert_equal(sb, StepType.RESEARCH.value, "research")
        sandbox.assert_equal(sb, StepType.PROCESSING.value, "processing")
        sandbox.assert_equal(sb, StepType.REPORT.value, "report")


# ── Plan model ───────────────────────────────────────────────────────────────

def _make_plan(*step_types: str) -> Plan:
    steps = [
        Step(need_search=True, title=f"Step {i}", description="desc", step_type=st)
        for i, st in enumerate(step_types)
    ]
    return Plan(has_enough_context=True, thought="analysis", title="Test Plan", steps=steps)


class TestPlan:
    def test_empty_plan(self, sb):
        plan = Plan(has_enough_context=True, thought="t", title="T", steps=[])
        sandbox.assert_equal(sb, plan.get_research_steps(), [])
        sandbox.assert_equal(sb, plan.get_next_unexecuted_research_team_step(), None)
        sandbox.assert_equal(sb, plan.get_completed_steps(), [])

    def test_get_research_steps_filters_correctly(self, sb):
        """Bug fix: step.step_type in set, not Step-object in set."""
        plan = _make_plan("research", "processing", "report", "excel_analysing")
        steps = plan.get_research_steps()
        types = {s.step_type for s in steps}
        sandbox.assert_in(sb, "research", types)
        sandbox.assert_in(sb, "processing", types)
        sandbox.assert_in(sb, "excel_analysing", types)
        assert "report" not in types, "report should not be a research step"

    def test_get_next_unexecuted_returns_first_without_result(self, sb):
        plan = _make_plan("research", "processing")
        plan.steps[0].execution_res = "done"  # first step already done
        nxt = plan.get_next_unexecuted_research_team_step()
        sandbox.assert_not_none(sb, nxt)
        sandbox.assert_equal(sb, nxt.step_type, "processing")

    def test_get_next_unexecuted_returns_none_when_all_done(self, sb):
        plan = _make_plan("research")
        plan.steps[0].execution_res = "done"
        sandbox.assert_equal(sb, plan.get_next_unexecuted_research_team_step(), None)

    def test_get_completed_steps(self, sb):
        plan = _make_plan("research", "processing")
        plan.steps[0].execution_res = "result A"
        completed = plan.get_completed_steps()
        sandbox.assert_equal(sb, len(completed), 1)
        sandbox.assert_equal(sb, completed[0].step_type, "research")

    def test_plan_to_json(self, sb):
        plan = _make_plan("research")
        json_str = plan.to_json(indent=2)
        assert "research" in json_str

    def test_has_enough_context_flag(self, sb):
        plan = Plan(has_enough_context=False, thought="need more", title="T", steps=[])
        sandbox.assert_equal(sb, plan.has_enough_context, False)


# ── STEP_TYPE_TO_NODE_MAP ────────────────────────────────────────────────────

class TestStepTypeNodeMap:
    def test_map_values_are_strings(self, sb):
        """Values must be plain strings (builder.py does NOT call .value on them)."""
        for key, val in STEP_TYPE_TO_NODE_MAP.items():
            sandbox.assert_true(sb, isinstance(val, str), f"{key} → {val!r} must be str")

    def test_research_maps_to_researcher(self, sb):
        sandbox.assert_equal(sb, STEP_TYPE_TO_NODE_MAP[StepType.RESEARCH], "researcher")

    def test_processing_maps_to_coder(self, sb):
        sandbox.assert_equal(sb, STEP_TYPE_TO_NODE_MAP[StepType.PROCESSING], "coder")

    def test_report_maps_to_reporter(self, sb):
        sandbox.assert_equal(sb, STEP_TYPE_TO_NODE_MAP[StepType.REPORT], "reporter")
