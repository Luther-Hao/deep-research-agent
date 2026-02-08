from typing import Any, Optional, Dict


class ConfigLoader:
    """配置文件加载器"""
    _config_cache: Optional[Dict[str,Any]] = None

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """加载配置文件，首次加载之后保存到缓存当中"""
        if cls._config_cache is not None:
            return cls._config_cache

        root_dir = ProjectRootFinder.get_project_root()


