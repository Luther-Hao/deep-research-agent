import configparser
from typing import Dict, Any

from src.infrastructure.config.config_loader import ConfigLoader


def _get_global_config() -> Dict[str, Any]:
    """获取全局配置（base_url api_key）"""
    global_config = {}

    full_config = ConfigLoader.load_config()

    if "CLOBAL_LLM_API_KEY" in full_config:
        global_config.update(full_config["CLOBAL_LLM_API_KEY"])

    return global_config

class LLMManager:
    pass

llm_manager = LLMManager()

