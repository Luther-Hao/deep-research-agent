from enum import Enum
from typing import Dict, Any


class ModelName(Enum):
    """基于OpenAI API的模型实例管理"""
    DEEPSEEK_CHAT = {
        "name":"deepseek-chat",
        "config":{
            "timeout": 60,
            "max_retries": 3
        }
    }



    @property
    def model_name(self) -> str:
        return self.value["name"]


    @property
    def config(self) -> Dict[str, Any]:
        return self.value["config"]


    def get_config_value(self, name: str):
        return self.config.get(name, "")

    @classmethod
    def from_name(cls, name: str):
        """根据模型名称字符串获取枚举模型实例"""
        if not name or not name.strip():
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"{cls.__name__}: invalid model name: {name},use DEEPSEEK_CHAT")
            return cls.DEEPSEEK_CHAT

        for model in cls:
            if model.model_name.lower() == name.lower():
                return model

        raise ValueError(f"invalid model name: {name}")

