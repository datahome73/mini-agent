"""
工具注册表 — 管理所有可用工具。
"""

from typing import Any

from tools.base import Tool


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_schemas(self) -> list[dict[str, Any]]:
        """返回所有工具的 OpenAI 格式 schema 列表"""
        return [t.to_openai_schema() for t in self._tools.values()]

    def describe(self) -> str:
        """返回人类可读的工具列表（给 system prompt 用）"""
        lines = []
        for t in self._tools.values():
            lines.append(f"- **{t.name}**: {t.description}")
        return "\n".join(lines)
