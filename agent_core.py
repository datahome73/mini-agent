"""
Agent 核心 — Loop + Runner 合二为一。

流程：
  收到消息 → 加载身份/记忆/会话 → 组装上下文 → 调 LLM
  → 如果有工具调用 → 逐个执行 → 结果喂回 LLM → 重复
  → 最终回复 → 存入会话 → 返回

也支持流式输出（process_message_stream），逐 token yield 文本片段。
"""

import logging
from typing import Any, AsyncGenerator

from bus import InboundMessage, OutboundMessage
from provider.deepseek import DeepSeekProvider
from tools.registry import ToolRegistry
from memory.session import SessionMemory
from memory.long_term import LongTermMemory

logger = logging.getLogger(__name__)


class AgentCore:
    """Agent 核心"""

    def __init__(
        self,
        provider: DeepSeekProvider,
        tool_registry: ToolRegistry,
        session_memory: SessionMemory,
        long_term_memory: LongTermMemory,
        max_tool_iterations: int = 10,
        session_history_size: int = 20,
    ):
        self.provider = provider
        self.tools = tool_registry
        self.sessions = session_memory
        self.ltm = long_term_memory
        self.max_tool_iterations = max_tool_iterations
        self.session_history_size = session_history_size

    async def process_message(self, msg: InboundMessage) -> OutboundMessage:
        """处理一条入站消息，返回出站回复（非流式）"""
        try:
            reply_text = await self._process(msg)
        except Exception as e:
            logger.exception("处理消息时异常")
            reply_text = f"内部错误：{e}"

        self.sessions.append(msg.session_id, "user", msg.text)
        self.sessions.append(msg.session_id, "assistant", reply_text)

        return OutboundMessage(
            text=reply_text,
            channel=msg.channel,
            chat_id=msg.chat_id,
            session_id=msg.session_id,
        )

    async def process_message_stream(
        self, msg: InboundMessage
    ) -> AsyncGenerator[str, None]:
        """
        流式处理消息。
        先保存用户消息，然后逐 token yield 助手回复文本。
        工具调用阶段不 yield；只在最终文本输出时流式。
        """
        full_text = ""
        try:
            self.sessions.append(msg.session_id, "user", msg.text)

            async for chunk in self._process_stream(msg):
                full_text += chunk
                yield chunk

        except Exception as e:
            logger.exception("流式处理消息时异常")
            err = f"内部错误：{e}"
            yield err
            if not full_text:
                full_text = err

        self.sessions.append(msg.session_id, "assistant", full_text)

    # ---- 内部实现 ----

    def _build_messages(self, msg: InboundMessage) -> list[dict]:
        """组装消息列表（system + 历史 + 当前用户消息）"""
        history = self.sessions.get_recent(msg.session_id, self.session_history_size)
        identity_text = self.ltm.load_identity()
        memory_text = self.ltm.load()
        tools_desc = self.tools.describe()
        tool_schemas = self.tools.get_schemas()

        system_prompt = identity_text
        if memory_text:
            system_prompt += f"\n\n## 当前记忆\n{memory_text}"
        if tools_desc:
            system_prompt += f"\n\n## 可用工具\n{tools_desc}"

        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append(h)
        messages.append({"role": "user", "content": msg.text})
        return messages

    async def _process(self, msg: InboundMessage) -> str:
        """非流式核心处理逻辑"""
        messages = self._build_messages(msg)
        tool_schemas = self.tools.get_schemas()

        for iteration in range(self.max_tool_iterations):
            logger.info(f"Agent 迭代 {iteration + 1}/{self.max_tool_iterations}")

            result = self.provider.chat(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
            )

            if result["type"] == "text":
                return result["content"] or "(空回复)"

            tool_calls = result["content"]
            for tc in tool_calls:
                name = tc["name"]
                args = tc["args"]
                tool_id = tc["id"]

                logger.info(f"  调用工具: {name}({args})")
                self._append_tool_result(
                    messages, tc,
                    await self._execute_tool(name, args, tool_id),
                )

        return "抱歉，我思考了太久还没得出答案，请简化你的问题。"

    async def _process_stream(self, msg: InboundMessage) -> AsyncGenerator[str, None]:
        """流式核心处理逻辑。yield 文本片段。"""
        messages = self._build_messages(msg)
        tool_schemas = self.tools.get_schemas()

        for iteration in range(self.max_tool_iterations):
            logger.info(f"Agent 迭代 {iteration + 1}/{self.max_tool_iterations}")

            tool_calls_result = None
            async for chunk in self.provider.chat_stream(
                messages, tool_schemas if tool_schemas else None,
            ):
                if chunk["type"] == "text":
                    yield chunk["content"]
                elif chunk["type"] == "tool_calls":
                    tool_calls_result = chunk["content"]

            if tool_calls_result is None:
                return  # 纯文本，流式完成

            # 处理工具调用（非流式，和现有逻辑一致）
            for tc in tool_calls_result:
                name = tc["name"]
                args = tc["args"]
                tool_id = tc["id"]
                logger.info(f"  调用工具: {name}({args})")
                result_text = await self._execute_tool(name, args, tool_id)
                self._append_tool_result(messages, tc, result_text)

        yield "抱歉，我思考了太久还没得出答案，请简化你的问题。"

    async def _execute_tool(self, name: str, args: dict, tool_id: str) -> str:
        """执行单个工具调用，返回结果文本"""
        tool = self.tools.get(name)
        if tool is None:
            return f"错误：工具 '{name}' 不存在"
        try:
            result_text = await tool.fn(**args)
            if not isinstance(result_text, str):
                result_text = str(result_text)
            return result_text
        except Exception as e:
            return f"工具执行失败：{e}"

    def _append_tool_result(self, messages: list[dict], tc: dict, result_text: str):
        """把工具调用和结果追加到消息列表"""
        messages.append({
            "role": "assistant",
            "tool_calls": [{
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": str(tc["args"])},
            }],
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": result_text[:3000],
        })
