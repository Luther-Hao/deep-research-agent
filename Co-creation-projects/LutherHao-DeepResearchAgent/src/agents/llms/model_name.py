from enum import Enum
from typing import Dict, Any


class ModelName(Enum):
    """基于OpenAI API的模型实例管理"""
    DEEPSEEK_V3 = {
        "name":"deepseek-v3",
        "config":{
            "timeout": 60,
            "max_retry": 3
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

