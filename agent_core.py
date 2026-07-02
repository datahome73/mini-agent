"""
Agent 核心 — Loop + Runner 合二为一。

流程：
  收到消息 → 加载记忆和会话 → 组装上下文 → 调 LLM
  → 如果有工具调用 → 逐个执行 → 结果喂回 LLM → 重复
  → 最终回复 → 存入会话 → 返回
"""

import logging
from typing import Any

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
        """处理一条入站消息，返回出站回复"""
        try:
            reply_text = await self._process(msg)
        except Exception as e:
            logger.exception("处理消息时异常")
            reply_text = f"内部错误：{e}"

        # 保存到会话
        self.sessions.append(msg.session_id, "user", msg.text)
        self.sessions.append(msg.session_id, "assistant", reply_text)

        return OutboundMessage(
            text=reply_text,
            channel=msg.channel,
            chat_id=msg.chat_id,
            session_id=msg.session_id,
        )

    async def _process(self, msg: InboundMessage) -> str:
        """核心处理逻辑"""
        # 加载历史
        history = self.sessions.get_recent(msg.session_id, self.session_history_size)

        # 加载长期记忆
        memory_text = self.ltm.load()

        # 工具描述
        tools_desc = self.tools.describe()
        tool_schemas = self.tools.get_schemas()

        # 构建消息
        messages = self.provider.build_messages(
            user_text=msg.text,
            history=history,
            memory_text=memory_text,
            tools_description=tools_desc,
        )

        # 工具调用循环
        for iteration in range(self.max_tool_iterations):
            logger.info(f"Agent 迭代 {iteration + 1}/{self.max_tool_iterations}")

            result = self.provider.chat(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
            )

            if result["type"] == "text":
                return result["content"] or "(空回复)"

            # 处理工具调用
            tool_calls = result["content"]
            for tc in tool_calls:
                name = tc["name"]
                args = tc["args"]
                tool_id = tc["id"]

                logger.info(f"  调用工具: {name}({args})")
                tool = self.tools.get(name)

                if tool is None:
                    result_text = f"错误：工具 '{name}' 不存在"
                else:
                    try:
                        result_text = await tool.fn(**args)
                        if not isinstance(result_text, str):
                            result_text = str(result_text)
                    except Exception as e:
                        result_text = f"工具执行失败：{e}"

                # 把工具调用和结果加入消息列表
                messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {"name": name, "arguments": str(args)},
                    }],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result_text[:3000],
                })

        return "抱歉，我思考了太久还没得出答案，请简化你的问题。"
