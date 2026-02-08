import configparser
from typing import Dict, Any, Union, Optional

from langchain_openai.chat_models.base import BaseChatOpenAI
from openai import OpenAI

from src.agents.llms.model_name import ModelName
from src.infrastructure.config.config_loader import ConfigLoader

import logging
logging.basicConfig(level=logging.DEBUG)

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
        model_str = model_name.model_name
        model_config = model_name.config

        base_config = {
            "model": model_str,
            "base_url": self._global_config.get("base_url"),
            "api_key": self._global_config.get("api_key"),
            "temperature": 0
        }
        total_config = {**base_config, **model_config,**kwargs}
        logging.debug(f"最终模型配置：{total_config}")
        return BaseChatOpenAI(**total_config)

    def get_model_by_name(self, model_name: str, **kwargs) -> BaseChatOpenAI:
        try:
            model_enum = ModelName.from_name(model_name)
            return self.get_model(model_enum, **kwargs)
        except ValueError:
            return self.get_model(ModelName.DEEPSEEK_CHAT,**kwargs)



    def get_model(self, model_enum: ModelName, **kwargs) -> BaseChatOpenAI:
        """获取模型实例,利用缓存提高性能"""
        model_key = model_enum.model_name
        # TODO 多模型配置不同api key优化
        api_key = self._global_config.get("api_key")



llm_manager = LLMManager()

if __name__ == '__main__':
    llm = llm_manager._create_model_instance(ModelName.DEEPSEEK_CHAT)
    print(llm.invoke("你好"))


