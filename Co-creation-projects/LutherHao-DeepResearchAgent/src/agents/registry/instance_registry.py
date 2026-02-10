import logging
from typing import Type, Dict

from src.agents.base.base_agent import BaseAgent

logger = logging.getLogger(__name__)


def registry(name:str):
    """
    注册装饰器
    用于将Agent类注册到各种注册表当中
    """
    def decorator(cls: Type) -> Type:
        if not issubclass(cls, BaseAgent):
            raise TypeError(f"{cls} must be subclass of BaseAgent")
        try:
            register_agent_class(name, cls)
        except ImportError as e:
            logger.error(f"Import error: {e}")
            raise e
        return cls


class AgentInstanceRegistry:
    """Agent实例注册表"""

    def __init__(self):
        """初始化实例注册表"""
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}
        self._instances: Dict[str, BaseAgent] = {}
        self._instances_configs: Dict[str, dict] = {}

    def register_agent_class(self, name:str, agent_class: Type[BaseAgent]):
        """注册Agent类"""

        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"{agent_class} must be subclass of BaseAgent")

        self._agent_classes[name] = agent_class
        logger.info(f"Registered agent class {name}")



def get_instance_registry():
    """获取全局实例注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentInstanceRegistry()
    return _global_registry


def register_agent_class(name, cls):
    """全局函数，注册Agent类"""
    get_instance_registry().register_agent_class(name, cls)