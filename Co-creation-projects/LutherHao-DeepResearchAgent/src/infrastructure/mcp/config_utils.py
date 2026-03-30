from typing import Set, Dict, Any, List, Union

MCP_SERVER_CONFIG_FIELDS={
    "transport",
    "command",
    "args",
    "url",
    "env",
    "need_auth"
}

def extract_mcp_server_config(
    server_config: Dict[str, Any],
    additional_fields: Set[str] = None,
) -> Dict[str, Any]:
    """合并MCP Server的关键配置信息"""
    all_fields = MCP_SERVER_CONFIG_FIELDS
    if additional_fields:
        all_fields = all_fields.union(additional_fields)

    return {
        k: v
        for k, v in server_config.items()
        if k in  all_fields
    }

def normalize_enabled_tools(
        enabled_tools_list: Union[List[str], List[Dict[str, Any]]]) -> List[str]:
    """标准化工具列表，统一转换为字符串列表"""

    if not enabled_tools_list:
        return []

    if isinstance(enabled_tools_list[0], dict):
        # 字典列表格式,直接提取name字段
        return [tool["name"] for tool in enabled_tools_list if "name" in tool]
    else:
        return enabled_tools_list