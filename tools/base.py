"""
工具基类 — 每个工具是一个可调用的能力描述。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema
    fn: Callable[..., Coroutine[Any, Any, str] | str]
    requires_confirmation: bool | Callable[[dict], bool] = False

    def to_openai_schema(self) -> dict:
        """转为 OpenAI function calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def should_confirm(self, args: dict) -> bool:
        """判断给定参数是否需要人工确认"""
        if callable(self.requires_confirmation):
            return self.requires_confirmation(args)
        return self.requires_confirmation
