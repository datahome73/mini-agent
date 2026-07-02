"""
DeepSeek 提供者 — 通过 OpenAI 兼容接口调用 DeepSeek API。
"""

import json
import logging
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是南欧 🐈，一个极简的个人 AI 助手。

## 核心原则
- 用简洁的中文回答
- 不清楚的就说不知道，不要编造
- 需要时主动使用工具

## 可用工具
{tools_description}
"""


class DeepSeekProvider:
    """封装 DeepSeek 的 API 调用"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", model: str = "deepseek-chat"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def build_messages(
        self,
        user_text: str,
        history: list[dict],
        memory_text: str,
        tools_description: str,
    ) -> list[dict]:
        """组装完整的消息列表"""
        system = SYSTEM_PROMPT.format(tools_description=tools_description)
        if memory_text:
            system += f"\n\n## 长期记忆\n{memory_text}"

        messages = [{"role": "system", "content": system}]

        # 加入历史对话
        for h in history:
            messages.append(h)

        # 加入当前用户消息
        messages.append({"role": "user", "content": user_text})
        return messages

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        调用 DeepSeek。
        返回格式：
            {"type": "text", "content": "..."}
            {"type": "tool_calls", "content": [...]}
        """
        kwargs = dict(
            model=self.model,
            messages=messages,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"API 调用失败: {e}")
            return {"type": "text", "content": f"调用 DeepSeek API 失败：{e}"}

        choice = response.choices[0]
        msg = choice.message

        # 处理工具调用
        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": args,
                })
            return {"type": "tool_calls", "content": tool_calls}

        # 纯文本回复
        return {"type": "text", "content": msg.content or ""}
