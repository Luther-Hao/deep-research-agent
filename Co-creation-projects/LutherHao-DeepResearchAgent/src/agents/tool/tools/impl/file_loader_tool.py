import logging

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from pydantic import Field

logger = logging.getLogger(__name__)

class FileLoader(BaseTool):
    name: str = 'FileLoader'
    description: str = 'Loads files from disk'
    return_direct: bool = False
    message: list = Field(description="List of messages to process")
