import dataclasses
import os
from typing import Optional, Any

from langchain_core.runnables import RunnableConfig


@dataclasses.dataclass
class Configuration:
    """configurable fields"""
    max_plan_iterations: int = 1
    max_step_num: int = 3
    max_search_result: int = 3
    mcp_settings: dict = None
    model: str = None
    enable_visualization: bool = False

    @classmethod
    def from_runnable_config(cls,config : Optional[RunnableConfig] = None) -> "Configuration":
        """Create a configuration object from runnable config"""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in dataclasses.fields(cls)
            if f.init
        }

        return cls(**{k: v for k,v in values.items() if v})