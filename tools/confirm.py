"""
确认管理器 — 人工审批流（Human-in-the-Loop）。

管理每个会话中待用户确认的敏感操作。
挂起状态是会话级别的：不同会话可以各自挂起，互不干扰。
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 用户回复的确认语义
_AFFIRMATIVE = {"是", "yes", "y", "确认", "确认执行", "可以", "行", "好", "执行", "ok", "YES", "Yes"}
_NEGATIVE = {"否", "no", "不", "取消", "不执行", "不行", "不要", "算了", "NO", "No"}


@dataclass
class PendingAction:
    """一个挂起的待确认操作"""
    session_id: str
    tool_name: str
    tool_args: dict
    tool_id: str
    question: str
    messages: list = field(default_factory=list)
    """挂起时的消息列表（含 assistant tool_calls），恢复时复用"""


class ConfirmManager:
    """确认管理器 — 按 session 管理待确认操作"""

    def __init__(self):
        self._pending: dict[str, PendingAction] = {}

    def request(
        self,
        session_id: str,
        tool_name: str,
        tool_args: dict,
        tool_id: str,
        messages: list,
    ) -> str:
        """挂起一个敏感操作，返回要展示给用户的确认提示文本"""
        question = self._build_question(tool_name, tool_args)
        self._pending[session_id] = PendingAction(
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_id=tool_id,
            question=question,
            messages=messages,
        )
        logger.info(
            "审批挂起 [%s]: %s(%s)",
            session_id, tool_name, tool_args,
        )
        return question

    def is_pending(self, session_id: str) -> bool:
        """检查某会话是否有待确认操作"""
        return session_id in self._pending

    def resolve(self, session_id: str, user_text: str) -> str | None:
        """解析用户回复，返回 'approved' / 'rejected' / None（语义不明）"""
        text = user_text.strip().lower()
        if text in _AFFIRMATIVE:
            logger.info("审批通过 [%s]", session_id)
            return "approved"
        if text in _NEGATIVE:
            logger.info("审批拒绝 [%s]", session_id)
            return "rejected"
        return None

    def pop(self, session_id: str) -> PendingAction | None:
        """取出并清除挂起的操作（拿到后执行或丢弃）"""
        return self._pending.pop(session_id, None)

    def cancel(self, session_id: str):
        """取消挂起（不清除 messages，直接丢弃）"""
        self._pending.pop(session_id, None)
        logger.info("审批取消 [%s]", session_id)

    def get_tool_id(self, session_id: str) -> str | None:
        pending = self._pending.get(session_id)
        return pending.tool_id if pending else None

    def get_question(self, session_id: str) -> str | None:
        pending = self._pending.get(session_id)
        return pending.question if pending else None

    @staticmethod
    def _build_question(tool_name: str, args: dict) -> str:
        """生成确认提示文本"""
        arg_summary = ", ".join(
            f"{k}={v if len(str(v)) < 200 else str(v)[:200] + '...'}"
            for k, v in args.items()
        )
        return (
            f"⚠️ **需要你确认这个操作：**\n\n"
            f"工具：`{tool_name}`\n参数：`{arg_summary}`\n\n"
            f"回复「**是**」确认执行，或「**否**」取消。"
        )
