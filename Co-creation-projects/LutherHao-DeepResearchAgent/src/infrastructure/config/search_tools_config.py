import enum
import os

from dotenv import load_dotenv

load_dotenv()

class SearchEngine(enum.Enum):
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    BRAVE_SEARCH = "brave_search"
    ARXIV = "arxiv"


# Tools configuration
SEARCH_ENGINE = os.getenv("SEARCH_ENGINE", SearchEngine.TAVILY.value)