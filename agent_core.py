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
from memory.trace import TraceStore
from memory.context_manager import ContextManager, ContextReport
from tools import plan as plan_tools

logger = logging.getLogger(__name__)


class AgentCore:
    """Agent 核心"""

    def __init__(
        self,
        provider: DeepSeekProvider,
        tool_registry: ToolRegistry,
        session_memory: SessionMemory,
        long_term_memory: LongTermMemory,
        trace_store: TraceStore | None = None,
        context_manager: ContextManager | None = None,
        max_tool_iterations: int = 10,
        session_history_size: int = 20,
    ):
        self.provider = provider
        self.tools = tool_registry
        self.sessions = session_memory
        self.ltm = long_term_memory
        self.trace_store = trace_store
        self.context_manager = context_manager or ContextManager()
        self.max_tool_iterations = max_tool_iterations
        self.session_history_size = session_history_size
        self._last_context_report: ContextReport | None = None

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

    def format_last_trace(self, session_id: str) -> str:
        """返回指定会话最近一次 trace 的可读文本。"""
        if self.trace_store is None:
            return "trace 功能未启用。"
        return self.trace_store.format_last(session_id)

    def format_context_report(self) -> str:
        """返回最近一次上下文的预算使用报告"""
        return self.context_manager.format_report(self._last_context_report)

    def _build_messages(self, msg: InboundMessage) -> list[dict]:
        """组装消息列表（system + 历史 + 当前用户消息）

        使用 ContextManager 进行预算管理，超预算时自动截断旧消息。
        """
        history = self.sessions.get_recent(msg.session_id, self.session_history_size)
        identity_text = self.ltm.load_identity()
        memory_text = self.ltm.load()
        tools_desc = self.tools.describe()
        tool_schemas = self.tools.get_schemas()

        # 如果 load_skill 工具可用，在身份提示中加一条提示
        if self.tools.get("load_skill"):
            identity_text += (
                "\n\n## 技能系统（Skill）\n"
                "你有 load_skill 和 list_skills 工具，可以读取 skills/ 目录下的技能文档来学习新能力。\n"
                "遇到不熟悉的任务或流程时，先用 list_skills 看看有没有对应的技能，\n"
                "再用 load_skill 加载学习。\n"
            )

        # 如果规划工具可用，注入规划/执行提示
        if self.tools.get("create_plan"):
            identity_text += (
                "\n\n## 多步规划（Plan/Execute）\n"
                "对于需要多个步骤的复杂任务，请使用规划工具创建工作流：\n"
                "1. **create_plan** — 先列出执行步骤，不要直接动手。把目标写清楚，步骤列具体。\n"
                "2. 按步骤逐个执行，每完成一步调用 **complete_step** 标记完成。\n"
                "3. 如果中途发现遗漏或情况变化，用 **revise_plan** 插入新步骤。\n"
                "4. 随时可用 **get_plan** 查看当前进度。\n"
                "5. 全部步骤完成后，总结最终结果回复用户。\n"
                "\n"
                "注意：简单的单步工具调用不需要规划。只在需要 3+ 步且有依赖关系时使用。\n"
            )

            # 如果有活跃计划，在上下文中注入当前进度
            if plan_tools.has_active_plan():
                identity_text += f"\n### 当前计划进度\n{plan_tools.get_plan_summary()}\n"

        messages, report = self.context_manager.build_context(
            identity_text=identity_text,
            memory_text=memory_text,
            tools_desc=tools_desc,
            history=history,
            user_text=msg.text,
        )
        self._last_context_report = report
        return messages

    async def _process(self, msg: InboundMessage) -> str:
        """非流式核心处理逻辑"""
        messages = self._build_messages(msg)
        tool_schemas = self.tools.get_schemas()
        trace = TraceStore.new_trace(msg) if self.trace_store else None

        try:
            for iteration in range(self.max_tool_iterations):
                logger.info(f"Agent 迭代 {iteration + 1}/{self.max_tool_iterations}")

                result = self.provider.chat(
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                )
                trace_item = self._trace_iteration(trace, iteration + 1, result)

                if result["type"] == "text":
                    final_text = result["content"] or "(空回复)"
                    if trace is not None:
                        trace["final_answer"] = final_text
                    return final_text

                tool_calls = result["content"]
                reasoning = result.get("reasoning_content", "")

                # 一个 assistant 消息包含本轮所有 tool_calls（保留 reasoning_content）
                assistant_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": str(tc["args"]),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                if reasoning:
                    assistant_msg["reasoning_content"] = reasoning
                messages.append(assistant_msg)

                for tc in tool_calls:
                    name = tc["name"]
                    args = tc["args"]
                    tool_id = tc["id"]

                    logger.info(f"  调用工具: {name}({args})")
                    result_text = await self._execute_tool(name, args, tool_id)
                    self._trace_tool_result(trace_item, tc, result_text)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_text[:3000],
                    })

            final_text = "抱歉，我思考了太久还没得出答案，请简化你的问题。"
            if trace is not None:
                trace["final_answer"] = final_text
            return final_text
        except Exception as e:
            if trace is not None:
                trace["error"] = str(e)
            raise
        finally:
            if trace is not None:
                self.trace_store.save(trace)

    async def _process_stream(self, msg: InboundMessage) -> AsyncGenerator[str, None]:
        """流式核心处理逻辑。yield 文本片段。"""
        messages = self._build_messages(msg)
        tool_schemas = self.tools.get_schemas()
        trace = TraceStore.new_trace(msg) if self.trace_store else None
        final_text = ""

        try:
            for iteration in range(self.max_tool_iterations):
                logger.info(f"Agent 迭代 {iteration + 1}/{self.max_tool_iterations}")

                tool_calls_result = None
                tool_calls_reasoning = ""
                streamed_text = ""
                trace_item = {
                    "index": iteration + 1,
                    "result_type": "text",
                    "text_preview": "",
                    "tool_calls": [],
                }
                if trace is not None:
                    trace["iterations"].append(trace_item)

                async for chunk in self.provider.chat_stream(
                    messages, tool_schemas if tool_schemas else None,
                ):
                    if chunk["type"] == "text":
                        streamed_text += chunk["content"]
                        final_text += chunk["content"]
                        if trace_item is not None:
                            trace_item["text_preview"] = streamed_text[:1000]
                        yield chunk["content"]
                    elif chunk["type"] == "tool_calls":
                        tool_calls_result = chunk["content"]
                        tool_calls_reasoning = chunk.get("reasoning_content", "")

                if tool_calls_result is None:
                    if trace is not None:
                        trace["final_answer"] = final_text
                    return  # 纯文本，流式完成

                trace_item["result_type"] = "tool_calls"
                tc_list = tool_calls_result

                # 一个 assistant 消息包含本轮所有 tool_calls（保留 reasoning_content）
                assistant_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": str(tc["args"]),
                            },
                        }
                        for tc in tc_list
                    ],
                }
                if tool_calls_reasoning:
                    assistant_msg["reasoning_content"] = tool_calls_reasoning
                messages.append(assistant_msg)

                for tc in tc_list:
                    name = tc["name"]
                    args = tc["args"]
                    tool_id = tc["id"]
                    logger.info(f"  调用工具: {name}({args})")
                    result_text = await self._execute_tool(name, args, tool_id)
                    self._trace_tool_result(trace_item, tc, result_text)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_text[:3000],
                    })

            final_text = "抱歉，我思考了太久还没得出答案，请简化你的问题。"
            if trace is not None:
                trace["final_answer"] = final_text
            yield final_text
        except Exception as e:
            if trace is not None:
                trace["error"] = str(e)
            raise
        finally:
            if trace is not None:
                if final_text and not trace.get("final_answer"):
                    trace["final_answer"] = final_text
                self.trace_store.save(trace)

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

    def _trace_iteration(self, trace: dict | None, index: int, result: dict) -> dict | None:
        """Append one LLM iteration to the trace."""
        if trace is None:
            return None
        item = {
            "index": index,
            "result_type": result.get("type"),
            "text_preview": "",
            "tool_calls": [],
        }
        if result.get("type") == "text":
            item["text_preview"] = (result.get("content") or "")[:1000]
        trace["iterations"].append(item)
        return item

    def _trace_tool_result(self, trace_item: dict | None, tc: dict, result_text: str):
        """Append one tool call result to the current trace item."""
        if trace_item is None:
            return
        trace_item["tool_calls"].append({
            "id": tc.get("id"),
            "name": tc.get("name"),
            "args": tc.get("args", {}),
            "result_preview": result_text[:1000],
        })
