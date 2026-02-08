from dataclasses import dataclass
from typing import Optional, List


@dataclass
class AgentInfo:
    """Agent 信息"""
    id: str
    name: str
    description: str
    # 输入定义格式
    input_schema:Optional[List[dict[str, str]]] = None