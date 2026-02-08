import configparser
from typing import Dict, Any, Union, Optional

from langchain_openai.chat_models.base import BaseChatOpenAI

from src.agents.llms.model_name import ModelName
from src.infrastructure.config.config_loader import ConfigLoader


def _get_global_config() -> Dict[str, Any]:
    """获取全局配置（base_url api_key）"""
    global_config = {}

    full_config = ConfigLoader.load_config()

    if "GLOBAL_LLM_API_KEY" in full_config:
        global_config.update(full_config["GLOBAL_LLM_API_KEY"])

    return global_config

class LLMManager:
    """OpenAI兼容的模型管理器,使用BaseChatOpenAI创建模型实例"""
    def __init__(self):
        self._global_config = _get_global_config()

    def _create_model_instance(self, model_name: Optional[ModelName],**kwargs) -> BaseChatOpenAI:
        """根据模型名称创建对应的模型实例，使用BaseChatOpenAI"""
        model_str = model_name.name
        model_config = model_name.config

        base_config = {
            "model": model_str
        }
        total_config = {**base_config, **model_config}
        return BaseChatOpenAI(**total_config)


llm_manager = LLMManager()

