from typing import Any

MAX_TRUNCATE_LENGTH = 10000
def safe_truncate(value: Any, max_length: int = MAX_TRUNCATE_LENGTH) -> str:
    """截断字符并转换为安全字符串"""

    if value is None:
        return ""

    str_value = str(value)
    if len(str_value) > max_length:
        return str_value[:max_length] + "..."
    return str_value