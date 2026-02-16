import logging
from typing import Type, Any, TypeVar

from src.agents.tool.tools.impl.tavily_search_tool import MultiTavilySearch
from src.infrastructure.config.search_tools_config import SEARCH_ENGINE, SearchEngine

logger = logging.getLogger(__name__)

T = TypeVar('T')

class LoggedToolMixin:
    """A mixin class that adds logging functionality."""

    def _log_operation(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        tool_name = self.__class__.__name__.replace("Logged", "")
        params = ",".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        logger.debug(f"{tool_name}.{method_name}({params})")

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        self._log_operation("run", *args, **kwargs)
        result = super()._run(*args, **kwargs)
        logger.debug(
            f"Tool {self.__class__.__name__.replace("Logged","")} returned: {result}"
        )
        return result
def create_logged_tool(base_tool_class: Type[T]) -> Type[T]:
    """
    Create a logged tool based on a base tool class.
    :param base_tool_class:
    :return:
    """
    class LoggedTool(LoggedToolMixin, base_tool_class):
        pass

    LoggedTool.__name__ = f"Logged{base_tool_class.__name__}"
    return LoggedTool


LoggedTavilySearch = create_logged_tool(MultiTavilySearch)
# LoggedDuckDuckGoSearch = create_logged_tool(DuckDuckGoSearch)
# LoggedBraveSearch = create_logged_tool(BraveSearch)
# LoggedArxivSearch = create_logged_tool(ArxivQueryRun)


def get_web_search_tool(max_search_results: int):
    if SEARCH_ENGINE == SearchEngine.TAVILY.value:
        return LoggedTavilySearch(
            name="web_search",
            max_results=max_search_results,
            include_raw_content=True,
            include_images=True,
            include_image_description=True,
        )
    # elif SEARCH_ENGINE == SearchEngine.DUCKDUCKGO.value:
    #     return LoggedDuckDuckGoSearch(name="web_search", max_results=max_search_results)
    # elif SEARCH_ENGINE == SearchEngine.BRAVE_SEARCH.value:
    #     return LoggedArxivSearch(name="web_search", max_results=max_search_results)