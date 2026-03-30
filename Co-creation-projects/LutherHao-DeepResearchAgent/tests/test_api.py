"""
Tests for FastAPI endpoints (src/app/routers/).

Uses starlette TestClient; LLM and agent streaming are mocked so no
real API calls are made.
"""

import json
import pytest
from unittest.mock import patch, AsyncMock
from starlette.testclient import TestClient

from tests.sandbox import sandbox


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, sb, client):
        response = client.get("/api/health")
        sandbox.assert_equal(sb, response.status_code, 200)

    def test_health_body(self, sb, client):
        data = client.get("/api/health").json()
        sandbox.assert_equal(sb, data["status"], "healthy")
        sandbox.assert_in(sb, "service", data)


# ── Research stream endpoint ──────────────────────────────────────────────────

def _fake_stream_events():
    """Fake async generator that yields structured SSE events."""
    events = [
        {"type": "message", "role": "coordinator", "content": "开始研究..."},
        {"type": "message", "role": "planner", "content": "制定研究计划"},
        {"type": "final_report", "content": "# 测试报告\n\n内容"},
        {"type": "done"},
    ]
    return events


async def _mock_run_stream(*args, **kwargs):
    for e in _fake_stream_events():
        yield e


class TestResearchStreamEndpoint:
    def test_stream_returns_200(self, sb, client):
        with patch("src.app.routers.research.run_stream", side_effect=_mock_run_stream):
            with client.stream("POST", "/api/research/stream", json={"query": "test"}) as resp:
                sandbox.assert_equal(sb, resp.status_code, 200)

    def test_stream_content_type_is_event_stream(self, sb, client):
        with patch("src.app.routers.research.run_stream", side_effect=_mock_run_stream):
            with client.stream("POST", "/api/research/stream", json={"query": "test"}) as resp:
                ct = resp.headers.get("content-type", "")
                sandbox.assert_in(sb, "text/event-stream", ct)

    def test_stream_emits_sse_events(self, sb, client):
        with patch("src.app.routers.research.run_stream", side_effect=_mock_run_stream):
            with client.stream("POST", "/api/research/stream", json={"query": "test"}) as resp:
                lines = []
                for line in resp.iter_lines():
                    if line:
                        lines.append(line)

        data_lines = [l for l in lines if l.startswith("data: ")]
        sandbox.assert_true(sb, len(data_lines) > 0, "must emit at least one data: line")

    def test_stream_contains_final_report(self, sb, client):
        with patch("src.app.routers.research.run_stream", side_effect=_mock_run_stream):
            with client.stream("POST", "/api/research/stream", json={"query": "test"}) as resp:
                raw = resp.read().decode()

        sandbox.assert_in(sb, "final_report", raw)
        sandbox.assert_in(sb, "测试报告", raw)

    def test_stream_contains_done_signal(self, sb, client):
        with patch("src.app.routers.research.run_stream", side_effect=_mock_run_stream):
            with client.stream("POST", "/api/research/stream", json={"query": "test"}) as resp:
                raw = resp.read().decode()

        sandbox.assert_in(sb, "[DONE]", raw)

    def test_empty_query_uses_empty_string(self, sb, client):
        """Endpoint accepts empty query; run_stream raises ValueError internally."""
        async def _raise(*a, **kw):
            raise ValueError("User input cannot be empty.")
            yield  # make it an async generator

        with patch("src.app.routers.research.run_stream", side_effect=_raise):
            with client.stream("POST", "/api/research/stream", json={"query": ""}) as resp:
                raw = resp.read().decode()
        # Error should be surfaced in the SSE stream
        sandbox.assert_in(sb, "error", raw)

    def test_stream_default_params(self, sb, client):
        """Verify default params (max_plan_iterations=1, max_step_num=3) are accepted."""
        received_kwargs = {}

        async def _capture(*args, **kwargs):
            received_kwargs.update(kwargs)
            received_kwargs["query"] = args[0] if args else kwargs.get("user_input")
            yield {"type": "done"}

        with patch("src.app.routers.research.run_stream", side_effect=_capture):
            with client.stream("POST", "/api/research/stream", json={"query": "hello"}) as resp:
                resp.read()
