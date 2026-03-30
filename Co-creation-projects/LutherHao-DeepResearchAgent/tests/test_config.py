"""
Tests for configuration infrastructure:
  - src/infrastructure/config/configuration.py  (Configuration dataclass)
  - src/infrastructure/config/config_loader.py   (ConfigLoader YAML loading)
  - src/infrastructure/projectpath/project_root_finder.py  (ProjectRootFinder)
  - src/infrastructure/mcp/config_utils.py  (MCP helpers)
"""

import os
import pytest
import yaml

from tests.sandbox import sandbox
from src.infrastructure.config.configuration import Configuration
from src.infrastructure.mcp.config_utils import (
    extract_mcp_server_config,
    normalize_enabled_tools,
)


# ── Configuration ─────────────────────────────────────────────────────────────

class TestConfiguration:
    def test_defaults(self, sb):
        cfg = Configuration()
        sandbox.assert_equal(sb, cfg.max_plan_iterations, 1)
        sandbox.assert_equal(sb, cfg.max_step_num, 3)
        sandbox.assert_equal(sb, cfg.max_search_result, 3)
        sandbox.assert_equal(sb, cfg.enable_visualization, False)

    def test_from_runnable_config(self, sb):
        rc = {
            "configurable": {
                "max_plan_iterations": 2,
                "max_step_num": 5,
                "max_search_result": 10,
            }
        }
        cfg = Configuration.from_runnable_config(rc)
        sandbox.assert_equal(sb, cfg.max_plan_iterations, 2)
        sandbox.assert_equal(sb, cfg.max_step_num, 5)
        sandbox.assert_equal(sb, cfg.max_search_result, 10)

    def test_from_empty_config(self, sb):
        cfg = Configuration.from_runnable_config(None)
        # defaults apply
        sandbox.assert_equal(sb, cfg.max_plan_iterations, 1)

    def test_from_runnable_config_partial(self, sb):
        rc = {"configurable": {"max_plan_iterations": 3}}
        cfg = Configuration.from_runnable_config(rc)
        sandbox.assert_equal(sb, cfg.max_plan_iterations, 3)
        sandbox.assert_equal(sb, cfg.max_step_num, 3)  # still default


# ── ConfigLoader ──────────────────────────────────────────────────────────────

class TestConfigLoader:
    def test_loads_real_config(self, sb):
        """ConfigLoader should successfully load the project's application.yaml."""
        from src.infrastructure.config.config_loader import ConfigLoader
        ConfigLoader.clean_cache()
        config = ConfigLoader.load_config()
        sandbox.assert_not_none(sb, config)
        sandbox.assert_in(sb, "GLOBAL_LLM_API_KEY", config)

    def test_cache_returns_same_object(self, sb):
        from src.infrastructure.config.config_loader import ConfigLoader
        ConfigLoader.clean_cache()
        first = ConfigLoader.load_config()
        second = ConfigLoader.load_config()
        sandbox.assert_true(sb, first is second, "cache must return same object")

    def test_clean_cache_reloads(self, sb):
        from src.infrastructure.config.config_loader import ConfigLoader
        first = ConfigLoader.load_config()
        ConfigLoader.clean_cache()
        second = ConfigLoader.load_config()
        # After clean + reload, we get a new dict (equal in content but different object)
        sandbox.assert_equal(sb, first, second)

    def test_missing_config_raises(self, sb, tmp_path, monkeypatch):
        """ConfigLoader raises FileNotFoundError when config is absent."""
        from src.infrastructure.config.config_loader import ConfigLoader
        from src.infrastructure.projectpath.project_root_finder import ProjectRootFinder
        ConfigLoader.clean_cache()
        monkeypatch.setattr(ProjectRootFinder, "get_project_root", staticmethod(lambda: str(tmp_path)))
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load_config()
        ConfigLoader.clean_cache()

    def test_loads_from_sandbox_workdir(self, sb, monkeypatch):
        """ConfigLoader loads from a custom workdir (sandbox-seeded yaml)."""
        from src.infrastructure.config.config_loader import ConfigLoader
        from src.infrastructure.projectpath.project_root_finder import ProjectRootFinder
        ConfigLoader.clean_cache()
        monkeypatch.setattr(ProjectRootFinder, "get_project_root", staticmethod(lambda: sb.workdir))
        config = ConfigLoader.load_config()
        sandbox.assert_in(sb, "GLOBAL_LLM_API_KEY", config)
        sandbox.assert_equal(sb, config["GLOBAL_LLM_API_KEY"]["api_key"], "sk-test-mock-key-000000")
        ConfigLoader.clean_cache()  # restore default on teardown


# ── ProjectRootFinder ─────────────────────────────────────────────────────────

class TestProjectRootFinder:
    def test_finds_application_yaml(self, sb):
        """Project root contains application.yaml — finder should locate it."""
        from src.infrastructure.projectpath.project_root_finder import ProjectRootFinder
        root = ProjectRootFinder.get_project_root()
        sandbox.assert_true(sb, os.path.isdir(root), f"root must be a dir: {root}")
        sandbox.assert_true(
            sb,
            os.path.exists(os.path.join(root, "application.yaml")),
            "root must contain application.yaml",
        )

    def test_finds_marker_in_sandbox_workdir(self, sb):
        """Finder locates a workdir that contains application.yaml."""
        from src.infrastructure.projectpath.project_root_finder import ProjectRootFinder
        result = ProjectRootFinder.find_by_markers(
            start_path=sb.workdir,
            makers=["application.yaml"],
        )
        sandbox.assert_equal(sb, result, sb.workdir)


# ── MCP config utils ──────────────────────────────────────────────────────────

class TestMcpConfigUtils:
    _server_cfg = {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-github-trending"],
        "enable_tools": ["get_github_trending_repositories"],
        "add_to_agents": ["researcher"],
    }

    def test_extract_mcp_server_config(self, sb):
        result = extract_mcp_server_config(self._server_cfg)
        sandbox.assert_equal(sb, result["transport"], "stdio")
        sandbox.assert_equal(sb, result["command"], "uvx")
        assert "enable_tools" not in result, "extract should strip tool lists"

    def test_extract_mcp_server_config_with_additional_fields(self, sb):
        result = extract_mcp_server_config(self._server_cfg, additional_fields={"add_to_agents"})
        sandbox.assert_in(sb, "add_to_agents", result)

    def test_normalize_enabled_tools_strings(self, sb):
        tools = normalize_enabled_tools(["tool_a", "tool_b"])
        sandbox.assert_equal(sb, tools, ["tool_a", "tool_b"])

    def test_normalize_enabled_tools_dicts(self, sb):
        tools = normalize_enabled_tools([{"name": "tool_a"}, {"name": "tool_b"}])
        sandbox.assert_equal(sb, tools, ["tool_a", "tool_b"])

    def test_normalize_enabled_tools_empty(self, sb):
        sandbox.assert_equal(sb, normalize_enabled_tools([]), [])
        sandbox.assert_equal(sb, normalize_enabled_tools(None), [])
