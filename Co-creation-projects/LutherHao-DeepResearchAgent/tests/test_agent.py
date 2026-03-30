"""
Tests for src/agents/agent.py

Covers:
  - run_stream: yields structured events from a mocked graph
  - run_async: consumes stream without errors (mocked graph)
  - create_agent_dynamic: creates a ReAct agent with mocked LLM
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from langchain_core.messages import AIMessage, HumanMessage

from tests.sandbox import sandbox, LocalTestSandbox
from src.agents.agent import run_stream, create_agent_dynamic


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_graph_events(final_report: str = "# Report"):
    """Return fake astream events similar to what LangGraph emits."""
    return [
        {
            "messages": [HumanMessage(content="query"), AIMessage(content="Starting...", name="coordinator")],
            "observations": [],
            "final_report": "",
        },
        {
            "messages": [
                HumanMessage(content="query"),
                AIMessage(content="Starting...", name="coordinator"),
                AIMessage(content="Researching...", name="researcher"),
            ],
            "observations": ["obs1"],
            "final_report": "",
        },
        {
            "messages": [
                HumanMessage(content="query"),
                AIMessage(content="Starting...", name="coordinator"),
                AIMessage(content="Researching...", name="researcher"),
                AIMessage(content=final_report, name="reporter"),
            ],
            "observations": ["obs1"],
            "final_report": final_report,
        },
    ]


# ── run_stream ─────────────────────────────────────────────────────────────────

class TestRunStream:
    @pytest.mark.asyncio
    async def test_yields_message_events(self, sb):
        events = _make_graph_events()
        mock_stream = LocalTestSandbox.make_async_mock_stream(events)

        with patch("src.agents.agent.graph") as mock_graph:
            mock_graph.astream = mock_stream
            collected = [e async for e in run_stream("AI市场分析")]

        types = {e["type"] for e in collected}
        sandbox.assert_in(sb, "message", types)

    @pytest.mark.asyncio
    async def test_yields_final_report(self, sb):
        events = _make_graph_events(final_report="# 最终报告\n\n内容")
        mock_stream = LocalTestSandbox.make_async_mock_stream(events)

        with patch("src.agents.agent.graph") as mock_graph:
            mock_graph.astream = mock_stream
            collected = [e async for e in run_stream("test")]

        report_events = [e for e in collected if e["type"] == "final_report"]
        sandbox.assert_true(sb, len(report_events) == 1, "should yield exactly one final_report")
        sandbox.assert_equal(sb, report_events[0]["content"], "# 最终报告\n\n内容")

    @pytest.mark.asyncio
    async def test_yields_done_at_end(self, sb):
        mock_stream = LocalTestSandbox.make_async_mock_stream(_make_graph_events())

        with patch("src.agents.agent.graph") as mock_graph:
            mock_graph.astream = mock_stream
            collected = [e async for e in run_stream("test")]

        last = collected[-1]
        sandbox.assert_equal(sb, last["type"], "done")

    @pytest.mark.asyncio
    async def test_empty_input_raises(self, sb):
        with pytest.raises(ValueError, match="cannot be empty"):
            async for _ in run_stream(""):
                pass

    @pytest.mark.asyncio
    async def test_no_messages_key_skipped(self, sb):
        """Events without 'messages' key should not produce message events."""
        events = [{"observations": ["x"]}, {"final_report": "R", "observations": ["x"]}]
        mock_stream = LocalTestSandbox.make_async_mock_stream(events)

        with patch("src.agents.agent.graph") as mock_graph:
            mock_graph.astream = mock_stream
            collected = [e async for e in run_stream("test")]

        report_events = [e for e in collected if e["type"] == "final_report"]
        sandbox.assert_equal(sb, report_events[0]["content"], "R")


# ── run_async ─────────────────────────────────────────────────────────────────

class TestRunAsync:
    @pytest.mark.asyncio
    async def test_run_async_completes(self, sb):
        mock_stream = LocalTestSandbox.make_async_mock_stream(_make_graph_events())

        with patch("src.agents.agent.graph") as mock_graph:
            mock_graph.astream = mock_stream
            # Should complete without raising
            await __import__("src.agents.agent", fromlist=["run_async"]).run_async(
                user_input="test query"
            )

    @pytest.mark.asyncio
    async def test_run_async_empty_raises(self, sb):
        with pytest.raises(ValueError):
            from src.agents.agent import run_async
            await run_async("")


# ── create_agent_dynamic ───────────────────────────────────────────────────────

class TestCreateAgentDynamic:
    def test_returns_runnable_agent(self, sb):
        mock_model = sandbox.make_mock_llm()
        with patch("src.agents.agent.llm_manager") as mgr:
            mgr.get_model_by_name.return_value = mock_model
            agent = create_agent_dynamic("researcher", "researcher", [], "researcher", "deepseek-chat")

        sandbox.assert_not_none(sb, agent)
        sandbox.assert_true(sb, hasattr(agent, "ainvoke"), "agent must have .ainvoke")
