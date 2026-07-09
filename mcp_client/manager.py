"""
MCP 客户端管理器 — 连接 stdio MCP Server，获取工具列表并提供调用能力。

流程：
  加载 servers.json → 对每个 server 启动子进程 → MCP 协议握手
  → 获取 tools 列表 → 注册到 ToolRegistry → agent 可直接调用
"""
import json
import logging
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool, TextContent

logger = logging.getLogger(__name__)


class MCPServerConnection:
    """单个 MCP Server 的连接管理"""

    def __init__(self, name: str, command: str, args: list[str],
                 env: dict[str, str] | None = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.session: ClientSession | None = None
        self._stdio_ctx = None
        self._session_ctx = None
        self._connected = False

    async def connect(self) -> list[MCPTool]:
        """连接到 MCP server，返回工具列表"""
        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env={**os.environ, **(self.env or {})},
        )

        try:
            # 打开 stdio 传输
            self._stdio_ctx = stdio_client(params)
            read, write = await self._stdio_ctx.__aenter__()

            # 建立会话
            self._session_ctx = ClientSession(read, write)
            self.session = await self._session_ctx.__aenter__()
            await self.session.initialize()

            # 获取工具列表
            result = await self.session.list_tools()
            self._connected = True
            logger.info("MCP ✓ %s: %d 个工具", self.name, len(result.tools))
            return result.tools

        except Exception as e:
            logger.error("MCP ✗ %s 连接失败: %s", self.name, e)
            await self.disconnect()
            return []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """调用 MCP server 上的工具，返回文本结果"""
        if not self.session or not self._connected:
            return f"错误：MCP server '{self.name}' 未连接"

        try:
            result = await self.session.call_tool(name, arguments)
            # 拼接所有 content block 的文本
            parts = []
            for block in result.content:
                if isinstance(block, TextContent):
                    parts.append(block.text)
                else:
                    parts.append(str(block))
            output = "\n".join(parts)

            if result.isError:
                return f"错误：{output}"

            return output.strip() or "(工具返回空)"

        except Exception as e:
            return f"MCP 工具调用失败: {e}"

    async def disconnect(self):
        """断开连接，清理资源"""
        self._connected = False
        # 清理 MCP 上下文（如果 event loop 正在关闭，__aexit__ 可能抛 RuntimeError）
        for ctx in [self._session_ctx, self._stdio_ctx]:
            if ctx is not None:
                try:
                    await ctx.__aexit__(None, None, None)
                except (RuntimeError, Exception):
                    pass
        self.session = None
        self._session_ctx = None
        self._stdio_ctx = None

    @property
    def is_connected(self) -> bool:
        return self._connected


class MCPManager:
    """管理多个 MCP Server 连接"""

    def __init__(self, config_path: str = "mcp_client/servers.json"):
        self.config_path = config_path
        self.servers: dict[str, MCPServerConnection] = {}
        self._active_tools: list[dict] = []  # 所有 server 的工具描述

    async def load_all(self) -> list[dict]:
        """加载 servers.json，连接所有 server，返回工具描述列表。

        每个工具描述格式：
        {
            "name": "mcp_{server}_{tool}",      # 全局唯一
            "description": "...",
            "inputSchema": {...},
            "server": "server_name",
            "tool_name": "original_tool_name",
        }
        """
        if not os.path.isfile(self.config_path):
            logger.info("MCP 配置文件不存在: %s（跳过）", self.config_path)
            return []

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        server_configs = config.get("servers", [])
        if not server_configs:
            logger.info("MCP 配置为空（无 server）")
            return []

        self._active_tools = []

        for sc in server_configs:
            name = sc["name"]
            conn = MCPServerConnection(
                name=name,
                command=sc["command"],
                args=sc.get("args", []),
                env=sc.get("env"),
            )

            mcp_tools = await conn.connect()
            self.servers[name] = conn

            for t in mcp_tools:
                tool_name = f"mcp_{name}_{t.name}"
                self._active_tools.append({
                    "name": tool_name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema,
                    "server": name,
                    "tool_name": t.name,
                })

        return self._active_tools

    def get_server(self, name: str) -> MCPServerConnection | None:
        return self.servers.get(name)

    async def shutdown(self):
        """断开所有 MCP server 连接"""
        for name, conn in self.servers.items():
            logger.info("MCP 断开: %s", name)
            await conn.disconnect()
        self.servers.clear()
        self._active_tools.clear()

    @property
    def tool_count(self) -> int:
        return len(self._active_tools)
