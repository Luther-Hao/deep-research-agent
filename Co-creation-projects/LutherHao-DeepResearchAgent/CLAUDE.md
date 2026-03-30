# CLAUDE.md — Deep Research Agent

This file documents the architecture, development patterns, and engineering guidelines for this project. Claude Code must read this file at the start of every session and follow these rules strictly.

---

## Project Overview

A LangGraph-based deep research agent with a FastAPI backend and a simple static web frontend. The agent decomposes a research question into a structured plan, executes web research and data processing steps, and produces a comprehensive report.

---

## Architecture: Harness / App Split

The codebase enforces a hard boundary between two layers:

```
src/
├── agents/          # Harness — agent logic (LangGraph graph, nodes, LLMs, tools, prompts)
│   ├── agent.py         # run_async(), run_stream(), create_agent_dynamic()
│   ├── graph/
│   │   ├── builder.py       # build_graph() — LangGraph StateGraph assembly
│   │   └── nodes/
│   │       ├── nodes.py         # All node implementations
│   │       └── model/
│   │           ├── plan_model.py    # Plan, Step, StepType
│   │           └── types.py         # State (MessagesState)
│   ├── llms/
│   │   ├── llm_manager.py   # LLMManager singleton + model cache
│   │   └── model_name.py    # ModelName enum (DEEPSEEK_CHAT)
│   ├── prompt/
│   │   ├── template.py      # Jinja2 loader: get_prompt_template(), apply_prompt_template()
│   │   ├── coordinator.md   # Coordinator system prompt
│   │   ├── planner.md       # Planner system prompt
│   │   ├── researcher.md    # Researcher system prompt
│   │   ├── coder.md         # Coder system prompt
│   │   └── reporter.md      # Reporter system prompt
│   ├── tool/
│   │   ├── tool_manager.py  # ToolManager ABC, MCPToolManager, DefaultToolManager
│   │   └── tools/
│   │       ├── search_tool.py           # get_web_search_tool(), LoggedTavilySearch
│   │       └── impl/
│   │           ├── tavily_search_tool.py  # EnhancedTavilySearchWrapper, MultiTavilySearch
│   │           └── file_loader_tool.py    # FileLoader BaseTool
│   └── utils/
│       ├── data_utils.py    # safe_truncate()
│       └── json_utils.py    # repair_json_output()
│
├── app/             # App layer — FastAPI (imports from src.agents.*, src.infrastructure.*)
│   ├── api.py           # create_app() — FastAPI factory, mounts static/, registers routers
│   └── routers/
│       ├── health.py        # GET /api/health
│       └── research.py      # POST /api/research/stream  (SSE)
│
└── infrastructure/  # Shared infrastructure (no agent or app logic)
    ├── config/
    │   ├── configuration.py     # Configuration dataclass (from_runnable_config)
    │   ├── config_loader.py     # ConfigLoader — loads application.yaml with cache
    │   ├── search_tools_config.py  # SEARCH_ENGINE env var / SearchEngine enum
    │   └── questions.py         # BUILT_IN_QUESTIONS list
    ├── mcp/
    │   └── config_utils.py      # extract_mcp_server_config(), normalize_enabled_tools()
    └── projectpath/
        └── project_root_finder.py  # ProjectRootFinder — finds root by marker files
```

**Import firewall**: `src.agents.*` and `src.infrastructure.*` MUST NOT import from `src.app.*`. The app layer is a thin shell on top of the harness.

---

## Configuration

### `application.yaml` — DO NOT MODIFY API KEYS OR MODEL NAMES

```yaml
GLOBAL_LLM_API_KEY:
  base_url: "https://api.deepseek.com/v1"
  api_key: "<redacted>"

SEARCH_ENGINE:
  api: "tavily_search"
```

- `ConfigLoader.load_config()` reads this file; result is cached in-memory.
- To reload config without restart: call `ConfigLoader.clean_cache()`.
- `ProjectRootFinder` locates the project root by searching upward for `application.yaml` (primary) or `main.ipynb` (fallback).

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `SEARCH_ENGINE` | Search backend (`tavily`/`duckduckgo`/`brave_search`/`arxiv`) | `tavily` |
| `TAVILY_API_KEY` | Tavily API key | — |
| `LANGSMITH_API_KEY` | LangSmith tracing | — |
| `LANGSMITH_TRACING` | Enable tracing (`true`/`false`) | — |
| `AGENT_RECURSION_LIMIT` | Max recursion steps per sub-agent | `5` |
| `HOST` | Server bind host | `0.0.0.0` |
| `PORT` | Server bind port | `8000` |

Put secrets in `.env` (gitignored). A `.env.example` documents required keys.

---

## Research Workflow (LangGraph Graph)

```
START
  └─► coordinator_node
        ├─► (no tool call) → __end__
        └─► (handoff_to_planner)
              ├─► background_investigation_node (if enabled)
              │       └─► planner_node
              └─► planner_node
                    └─► human_feedback_node
                          ├─► planner (EDIT_PLAN)
                          ├─► __end__ (empty feedback)
                          └─► research_team_node
                                ├─► researcher_node  (step_type=research)
                                ├─► coder_node       (step_type=processing)
                                └─► reporter_node    (all steps done)
                                        └─► END
```

Key state fields in `State(MessagesState)`:
- `messages` — full message history
- `observations` — list of per-step research summaries
- `current_plan` — `Plan` Pydantic model
- `plan_iterations` — how many plan loops have run
- `final_report` — markdown string from reporter
- `enable_background_investigation` — bool
- `background_investigation_results` — raw text

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/research/stream` | Start research, returns SSE stream |
| `GET` | `/` | Static frontend (index.html) |
| `GET` | `/docs` | FastAPI Swagger UI |

### SSE Event Schema (`POST /api/research/stream`)

Request body:
```json
{
  "query": "string",
  "max_plan_iterations": 1,
  "max_step_num": 3,
  "enable_background_investigation": true
}
```

Events (newline-delimited `data: <json>\n\n`):

| `type` | Fields | Description |
|---|---|---|
| `message` | `role`, `content` | Agent message (coordinator/planner/researcher/…) |
| `final_report` | `content` | Completed markdown report |
| `error` | `message` | Error string |
| `done` | — | Stream end signal |

---

## Development Rules

### Adding a new agent node

1. Add a new function in `src/agents/graph/nodes/nodes.py` following the existing pattern.
2. Add the node to `_build_base_graph()` in `src/agents/graph/builder.py`.
3. Add a new prompt template `.md` in `src/agents/prompt/` if the node needs its own system prompt.
4. If the node handles a new `StepType`, add it to `plan_model.py::StepType` and `STEP_TYPE_TO_NODE_MAP`.

### Adding a new API endpoint

1. Create a new router file in `src/app/routers/`.
2. Register it in `src/app/api.py::create_app()` with `app.include_router(...)`.
3. The router MUST only import from `src.agents.*` or `src.infrastructure.*`, never internal `src.app.*` cross-imports.

### Modifying prompts

- Prompt templates are Jinja2 `.md` files in `src/agents/prompt/`.
- Available template variables: `CURRENT_TIME`, all fields from `State`, all fields from `Configuration`.
- Test prompt changes by running the agent with a simple query before committing.

### LLM model changes

- Add new models to `ModelName` enum in `src/agents/llms/model_name.py`.
- The `LLMManager` reads `base_url` and `api_key` from `application.yaml` automatically.
- Do NOT hardcode API keys anywhere in Python files.

### MCP tool integration

- MCP server configs live in the `config["configurable"]["mcp_settings"]` passed to `run_async`.
- To enable a tool for a specific agent, add it to `"enabled_tools"` and `"add_to_agents"` in the server config.

---

## Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env: add TAVILY_API_KEY, LANGSMITH_API_KEY, etc.

# Start the server
python main.py
# → http://localhost:8000  (web UI)
# → http://localhost:8000/docs  (API docs)
```

---

## Test Suite

### Running tests

```bash
# From the project root
python -m pytest tests/ -q              # all tests
python -m pytest tests/test_nodes.py   # specific file
python -m pytest -k "reporter"         # specific test by name
```

All 74 tests must pass before merging any change. Run the suite after every edit.

### Directory layout

```
tests/
├── __init__.py
├── conftest.py              # Session fixtures: sb (sandbox), client (TestClient)
├── pytest.ini               # asyncio_mode=auto, deprecation filters
├── sandbox/
│   ├── __init__.py
│   ├── base.py              # Abstract TestSandboxProvider + SandboxState
│   └── local_sandbox.py     # LocalTestSandbox — temp workdir, mock factories
├── test_plan_model.py       # Plan, Step, StepType, STEP_TYPE_TO_NODE_MAP
├── test_utils.py            # safe_truncate, repair_json_output, SearchEngine
├── test_config.py           # Configuration, ConfigLoader, ProjectRootFinder, MCP utils
├── test_builder.py          # get_next_research_step_node, build_graph
├── test_nodes.py            # coordinator, background_investigation, planner, reporter nodes
├── test_api.py              # FastAPI health + research/stream endpoints
└── test_agent.py            # run_stream, run_async, create_agent_dynamic
```

### Sandbox architecture (deer-flow pattern)

The `tests/sandbox/` layer mirrors deer-flow's `deerflow/sandbox/` pattern, adapted for test isolation:

| deer-flow sandbox | test sandbox equivalent |
|---|---|
| `SandboxProvider` ABC | `TestSandboxProvider` ABC (`tests/sandbox/base.py`) |
| `LocalSandboxProvider` | `LocalTestSandbox` (`tests/sandbox/local_sandbox.py`) |
| `SandboxState` (thread workdir) | `SandboxState` (test temp workdir + seeded `application.yaml`) |
| Acquires sandbox before tool execution | Acquires per-test isolated env via `sb` pytest fixture |

Every test receives a fresh `SandboxState` via the `sb` fixture (acquired/released around each test function). Assertion helpers (`sandbox.assert_equal`, `sandbox.assert_in`, etc.) embed the sandbox id in failure messages for easy debugging.

**Mock factories** on `LocalTestSandbox`:

| Factory | Returns |
|---|---|
| `sandbox.make_mock_llm(content, tool_calls)` | `MagicMock` acting as `BaseChatOpenAI` |
| `sandbox.make_mock_search(results)` | `MagicMock` acting as `LoggedTavilySearch` |
| `LocalTestSandbox.make_async_mock_stream(events)` | async generator for `graph.astream()` |

### Testing rules

1. **No real API calls** — every test that touches LLM or search must patch `llm_manager` or the tool class.
2. **Patch at the usage site** — patch `src.agents.graph.nodes.nodes.llm_manager`, not the original module.
3. **Use the `sb` fixture** — always obtain assertions through `sandbox.assert_*` for consistent error context.
4. **ConfigLoader cache** — tests that redirect `ProjectRootFinder.get_project_root` must call `ConfigLoader.clean_cache()` in teardown (use monkeypatch for automatic cleanup).
5. **Async tests** — mark with `@pytest.mark.asyncio`; `asyncio_mode = auto` is set globally in `pytest.ini`.

---

## Bug Fixes Applied (changelog)

The following bugs were found and fixed during initial development. Record new fixes here.

| File | Bug | Fix |
|---|---|---|
| `plan_model.py:get_research_steps()` | Compared `Step` object to string set instead of `step.step_type` | Changed `step in research_type` → `step.step_type in research_type` |
| `types.py` | Field named `plan_iteration` (singular) but nodes used `plan_iterations` (plural) | Renamed to `plan_iterations` |
| `nodes.py:reporter_node` | Incomplete function — no LLM call, no return statement | Fully implemented: invokes model, returns `{final_report, messages}` |
| `nodes.py:_get_available_tools_info_for_prompt` | `mcp_tools_info` used outside its defining `if` block → `NameError` | Moved `if mcp_tools_info:` inside the outer `if` block |
| `nodes.py:_run_research_team_step_with_agent` | `result["message"]` (typo) → `KeyError` | Fixed to `result["messages"]` |
| `nodes.py:_execute_research_team_step_with_tools` | Used `server_config["enabled_tools"]` but config key is `"enable_tools"` | Changed to `server_config.get("enabled_tools") or server_config.get("enable_tools", [])` |
| `builder.py:get_next_research_step_node` | Called `.value` on `STEP_TYPE_TO_NODE_MAP` values which are already plain strings | Removed `.value` |
| `mcp/config_utils.py:extract_mcp_server_config` | `additional_fields` was required but `nodes.py` called it with one arg | Made `additional_fields` optional (`= None`) |
| `project_root_finder.py` | Only searched for `main.ipynb`; `application.yaml` not a marker | Added `application.yaml` as primary marker |


| Decision | Rationale |
|---|---|
| LangGraph `StateGraph` for orchestration | Explicit state transitions, checkpointing, conditional routing |
| Harness / App split | Agent logic is testable and importable without running HTTP services |
| SSE for streaming | Simpler than WebSockets for unidirectional server→client events |
| Jinja2 prompt templates | Separates prompt content from Python code; supports dynamic context injection |
| `LLMManager` singleton with `lru_cache` | Avoids re-instantiating expensive model clients on every request |
| Static HTML/CSS/JS frontend | Zero build toolchain; instantly runnable without Node.js |
| `application.yaml` config (not `.env`) | Supports structured nested config (multi-model, multi-search-engine) beyond flat key=value |
