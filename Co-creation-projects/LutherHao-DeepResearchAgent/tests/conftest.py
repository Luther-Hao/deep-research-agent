"""
pytest conftest — session-wide fixtures and sandbox integration.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from tests.sandbox import sandbox, SandboxState


# ── Sandbox fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sb() -> SandboxState:
    """Acquire a fresh LocalTestSandbox for one test, release on teardown."""
    with sandbox.run() as state:
        yield state


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client() -> TestClient:
    from src.app.api import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)
