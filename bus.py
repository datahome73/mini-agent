"""
消息总线 — 极简的事件定义。
InboundMessage 从渠道进入，流向 agent_core。
OutboundMessage 从 agent_core 发出，由渠道发送给用户。
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class InboundMessage:
    """用户发来的消息"""
    channel: str            # "cli" | "telegram"
    text: str
    session_id: str
    chat_id: Optional[str] = None   # 渠道内的聊天标识
    raw: Any = None                 # 原始数据（调试用）


@dataclass
class OutboundMessage:
    """发给用户的消息"""
    text: str
    channel: str
    chat_id: Optional[str] = None
    session_id: Optional[str] = None
