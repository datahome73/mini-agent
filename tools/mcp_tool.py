"""
MCP 工具适配层 — 把 MCP 工具包装成 mini-agent 的 Tool 对象。
"""
import logging
from typing import Any

from tools.base import Tool
from mcp_client.manager import MCPManager

logger = logging.getLogger(__name__)


def _make_handler(mcp_manager: MCPManager, server_name: str, tool_name: str):
    """工厂函数：为单个 MCP 工具创建闭包 handler。"""
    async def handler(**kwargs: Any) -> str:
        conn = mcp_manager.get_server(server_name)
        if conn is None:
            return f"错误：MCP server '{server_name}' 未连接"
        return await conn.call_tool(tool_name, kwargs)

    handler.__name__ = f"mcp_{server_name}_{tool_name}"
    handler.__qualname__ = f"MCP.{server_name}.{tool_name}"
    return handler


def build_mcp_tools(mcp_manager: MCPManager) -> list[Tool]:
    """从 MCPManager 获取所有工具描述，包装成 mini-agent Tool 列表。

    命名规则：mcp_{server_name}_{tool_name}
    每个工具调用时通过 MCPManager 路由到对应的 server。
    """
    tools = []
    for td in mcp_manager._active_tools:
        name = td["name"]  # 如 "mcp_filesystem_read_file"
        server_name = td["server"]
        original_name = td["tool_name"]

        handler = _make_handler(mcp_manager, server_name, original_name)

        tool = Tool(
            name=name,
            description=td.get("description") or f"MCP 工具: {server_name}/{original_name}",
            parameters=td.get("inputSchema", {"type": "object", "properties": {}}),
            fn=handler,
        )
        tools.append(tool)

    return tools
