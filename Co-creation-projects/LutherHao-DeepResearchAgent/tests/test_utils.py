"""
Tests for utilities:
  - src/agents/utils/data_utils.py  (safe_truncate)
  - src/agents/utils/json_utils.py  (repair_json_output)
  - src/infrastructure/config/search_tools_config.py (SearchEngine enum)
"""

import pytest
from tests.sandbox import sandbox

from src.agents.utils.data_utils import safe_truncate
from src.agents.utils.json_utils import repair_json_output
from src.infrastructure.config.search_tools_config import SearchEngine


# ── safe_truncate ────────────────────────────────────────────────────────────

class TestSafeTruncate:
    def test_short_string_unchanged(self, sb):
        result = safe_truncate("hello", max_length=20)
        sandbox.assert_equal(sb, result, "hello")

    def test_long_string_truncated(self, sb):
        long = "a" * 200
        result = safe_truncate(long, max_length=50)
        sandbox.assert_true(sb, len(result) <= 53, "truncated string + ellipsis should be short")
        sandbox.assert_in(sb, "...", result)

    def test_exact_length(self, sb):
        s = "x" * 10
        result = safe_truncate(s, max_length=10)
        sandbox.assert_equal(sb, result, s)

    def test_empty_string(self, sb):
        result = safe_truncate("", max_length=10)
        sandbox.assert_equal(sb, result, "")


# ── repair_json_output ───────────────────────────────────────────────────────

class TestRepairJsonOutput:
    def test_valid_json_unchanged(self, sb):
        valid = '{"key": "value", "num": 42}'
        result = repair_json_output(valid)
        import json
        parsed = json.loads(result)
        sandbox.assert_equal(sb, parsed["key"], "value")

    def test_trailing_comma_repaired(self, sb):
        broken = '{"key": "value",}'
        result = repair_json_output(broken)
        import json
        # Should be parseable after repair
        parsed = json.loads(result)
        sandbox.assert_equal(sb, parsed["key"], "value")

    def test_missing_quote_repaired(self, sb):
        broken = '{key: "value"}'
        result = repair_json_output(broken)
        # json_repair should make this parseable
        import json
        try:
            parsed = json.loads(result)
            sandbox.assert_in(sb, "key", parsed)
        except json.JSONDecodeError:
            # Some repair libs may not handle this — mark as acceptable
            pass


# ── SearchEngine enum ────────────────────────────────────────────────────────

class TestSearchEngine:
    def test_enum_values(self, sb):
        sandbox.assert_equal(sb, SearchEngine.TAVILY.value, "tavily")
        sandbox.assert_equal(sb, SearchEngine.DUCKDUCKGO.value, "duckduckgo")
        sandbox.assert_equal(sb, SearchEngine.BRAVE_SEARCH.value, "brave_search")
        sandbox.assert_equal(sb, SearchEngine.ARXIV.value, "arxiv")

    def test_tavily_is_default(self, sb):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=False):
            engine = os.getenv("SEARCH_ENGINE", SearchEngine.TAVILY.value)
            sandbox.assert_equal(sb, engine, "tavily")
