"""DeepSeek 提供者 — 纯 API 调用，无业务逻辑。
仅负责将消息传给 LLM 并返回结果，不关心 prompt 内容。"""

import json
import logging
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class DeepSeekProvider:
    """封装 DeepSeek 的 API 调用"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        调用 LLM。
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
            return {"type": "text", "content": f"调用 API 失败：{e}"}

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
