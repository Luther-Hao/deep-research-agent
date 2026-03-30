"""
Sandbox — abstract base classes for test isolation.

Inspired by deer-flow's sandbox pattern (deerflow/sandbox/base.py):
- SandboxProvider: abstract factory that acquires/releases isolated environments
- SandboxState: dataclass holding runtime info about one sandbox instance

For tests, the sandbox manages:
  * A per-test temp workdir
  * Pre-seeded config files (application.yaml)
  * Result assertion helpers that embed sandbox context in failure messages
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class SandboxState:
    """Runtime state for one sandbox instance."""

    sandbox_id: str
    workdir: str
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"SandboxState(id={self.sandbox_id!r}, workdir={self.workdir!r})"


class TestSandboxProvider(ABC):
    """
    Abstract test sandbox provider.

    Mirrors deer-flow's SandboxProvider interface, adapted for unit/integration
    test isolation rather than code execution sandboxing.
    """

    @abstractmethod
    def acquire(self, test_id: str | None = None) -> SandboxState:
        """Acquire an isolated sandbox environment for one test."""
        ...

    @abstractmethod
    def release(self, state: SandboxState) -> None:
        """Release and clean up the sandbox after the test."""
        ...

    @contextmanager
    def run(self, test_id: str | None = None) -> Iterator[SandboxState]:
        """Context manager: acquire → yield state → release."""
        state = self.acquire(test_id or str(uuid.uuid4())[:8])
        try:
            yield state
        finally:
            self.release(state)

    # ── assertion helpers ────────────────────────────────────────────────────

    def assert_equal(self, state: SandboxState, actual: Any, expected: Any) -> None:
        """Assert equality, embedding sandbox id in the failure message."""
        assert actual == expected, (
            f"[sandbox:{state.sandbox_id}] Expected {expected!r}, got {actual!r}"
        )

    def assert_true(self, state: SandboxState, condition: bool, msg: str = "") -> None:
        assert condition, f"[sandbox:{state.sandbox_id}] {msg or 'Condition is False'}"

    def assert_not_none(self, state: SandboxState, value: Any) -> None:
        assert value is not None, f"[sandbox:{state.sandbox_id}] Value is None"

    def assert_in(self, state: SandboxState, item: Any, container: Any) -> None:
        assert item in container, (
            f"[sandbox:{state.sandbox_id}] {item!r} not found in {container!r}"
        )
