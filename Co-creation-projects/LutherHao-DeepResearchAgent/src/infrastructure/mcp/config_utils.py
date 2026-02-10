from typing import Set, Dict, Any

MCP_SERVER_CONFIG_FIELDS={
    "transport",
    "command",
    "args",
    "url",
    "env",
    "need_auth"
}

def extract_mcp_server_config(server_config : Dict[str, Any], additional_fields: Set[str]) -> Dict[str, Any]:
    """合并MCP Server的关键配置信息"""
    all_fields = MCP_SERVER_CONFIG_FIELDS
    if additional_fields:
        all_fields = all_fields.union(additional_fields)

    return {
        k: v
        for k, v in server_config.items()
        if k in  all_fields
    }