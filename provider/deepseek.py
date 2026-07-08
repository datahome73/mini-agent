"""DeepSeek 提供者 — 纯 API 调用，无业务逻辑。
仅负责将消息传给 LLM 并返回结果，不关心 prompt 内容。"""

import json
import logging
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger(__name__)


class DeepSeekProvider:
    """封装 DeepSeek 的 API 调用"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        同步调用 LLM（非流式）。
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

        # 提取 reasoning_content（DeepSeek thinking 模式）
        reasoning = getattr(msg, 'reasoning_content', None) or ''

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
            return {
                "type": "tool_calls",
                "content": tool_calls,
                "reasoning_content": reasoning,
            }

        # 纯文本回复
        return {"type": "text", "content": msg.content or ""}

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        异步流式调用 LLM。
        yield 格式（两种可能，最多各一）：
            {"type": "text", "content": "..."}      ← 文本片段（多个）
            {"type": "tool_calls", "content": [...]} ← 完整工具调用（结尾，仅一条）
        """
        kwargs = dict(
            model=self.model,
            messages=messages,
            stream=True,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self.async_client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"流式 API 调用失败: {e}")
            yield {"type": "text", "content": f"调用 API 失败：{e}"}
            return

        tool_call_deltas: dict[int, dict] = {}
        reasoning_content = ""

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # 累积 reasoning_content（DeepSeek thinking 模式）
            rc = getattr(delta, 'reasoning_content', None)
            if rc:
                reasoning_content += rc

            if delta.content:
                yield {"type": "text", "content": delta.content}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_call_deltas:
                        tool_call_deltas[idx] = {
                            "id": "",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        tool_call_deltas[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_call_deltas[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_call_deltas[idx]["function"]["arguments"] += tc.function.arguments

        if tool_call_deltas:
            tool_calls = []
            for idx in sorted(tool_call_deltas):
                tc = tool_call_deltas[idx]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": args,
                })
            yield {
                "type": "tool_calls",
                "content": tool_calls,
                "reasoning_content": reasoning_content,
            }
