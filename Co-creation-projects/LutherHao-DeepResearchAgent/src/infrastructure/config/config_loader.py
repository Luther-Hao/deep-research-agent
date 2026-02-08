import os
from typing import Any, Optional, Dict

import yaml

from src.infrastructure.projectpath.project_root_finder import ProjectRootFinder


class ConfigLoader:
    """配置文件加载器"""
    _config_cache: Optional[Dict[str,Any]] = None

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """加载配置文件，首次加载之后保存到缓存当中"""
        if cls._config_cache is not None:
            return cls._config_cache

        # 获取项目根目录
        root_dir = ProjectRootFinder.get_project_root()
        config_file = os.path.join(root_dir, "application.yaml")

        try:
            with open(config_file, "r",encoding='utf-8') as f:
                cls._config_cache = yaml.safe_load(f)
                return cls._config_cache
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file {config_file} not found.")


    @classmethod
    def clean_cache(cls):
        """清除缓存配置"""
        cls._config_cache = None



if __name__ == '__main__':
    print(ConfigLoader.load_config())
