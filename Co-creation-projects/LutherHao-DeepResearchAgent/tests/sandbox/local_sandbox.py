"""
Local test sandbox implementation.

Creates an isolated temp directory per test, seeds it with a minimal
application.yaml, and provides mock-object factories for LLM and search
so tests never make real network calls.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from unittest.mock import AsyncMock, MagicMock

import yaml

from .base import SandboxState, TestSandboxProvider

# ── Minimal config used by every sandbox instance ───────────────────────────

_TEST_CONFIG: dict = {
    "GLOBAL_LLM_API_KEY": {
        "base_url": "https://api.test.internal/v1",
        "api_key": "sk-test-mock-key-000000",
    },
    "SEARCH_ENGINE": {"api": "tavily_search"},
}


class LocalTestSandbox(TestSandboxProvider):
    """
    Local implementation of TestSandboxProvider.

    Each call to .acquire() creates a fresh temp directory and writes a
    minimal application.yaml into it, mirroring how LocalSandboxProvider
    in deer-flow sets up per-thread workspace directories.
    """

    def acquire(self, test_id: str | None = None) -> SandboxState:
        sid = test_id or str(uuid.uuid4())[:8]
        workdir = tempfile.mkdtemp(prefix=f"sandbox_{sid}_")

        # Seed the sandbox with a minimal config file
        config_path = os.path.join(workdir, "application.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(_TEST_CONFIG, f)

        return SandboxState(
            sandbox_id=sid,
            workdir=workdir,
            metadata={"config_path": config_path},
        )

    def release(self, state: SandboxState) -> None:
        if state.workdir and os.path.exists(state.workdir):
            shutil.rmtree(state.workdir, ignore_errors=True)

    # ── Mock factories ───────────────────────────────────────────────────────

    @staticmethod
    def make_mock_llm(
        response_content: str = "mock LLM response",
        tool_calls: list | None = None,
    ) -> MagicMock:
        """
        Return a MagicMock that behaves like a BaseChatOpenAI instance.

        - `.invoke(messages)` → AIMessage-like mock with .content and .tool_calls
        - `.bind_tools(tools)` → returns self (for coordinator_node)
        - `.with_structured_output(schema)` → returns self (for planner_node)
        """
        model = MagicMock(name="mock_llm")
        response = MagicMock(name="mock_response")
        response.content = response_content
        response.tool_calls = tool_calls if tool_calls is not None else []
        response.name = "mock"

        model.invoke.return_value = response
        model.bind_tools.return_value = model
        model.with_structured_output.return_value = model
        return model

    @staticmethod
    def make_mock_search(results: list | None = None) -> MagicMock:
        """Return a MagicMock that behaves like LoggedTavilySearch."""
        default = [
            {"title": "Test Result", "content": "This is test search content.", "url": "https://example.com"},
        ]
        tool = MagicMock(name="mock_search")
        tool.invoke.return_value = results if results is not None else default
        return tool

    @staticmethod
    def make_async_mock_stream(events: list | None = None):
        """
        Return an async generator mock that yields structured events.
        Used for mocking graph.astream() in agent tests.
        """

        async def _gen(*_args, **_kwargs):
            for event in (events or []):
                yield event

        return _gen


# ── Module-level singleton ───────────────────────────────────────────────────

sandbox = LocalTestSandbox()
