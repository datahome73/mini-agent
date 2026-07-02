"""
渠道抽象基类。
每个渠道负责从外部平台接收消息、发送回复。
"""

from abc import ABC, abstractmethod
from typing import Callable, Awaitable

from bus import InboundMessage, OutboundMessage


# 消息处理函数签名：收到 InboundMessage，返回 OutboundMessage
MessageHandler = Callable[[InboundMessage], Awaitable[OutboundMessage]]


class BaseChannel(ABC):
    """渠道基类。子类需要实现 start() 和 send()。"""

    def __init__(self, name: str):
        self.name = name
        self._handler: MessageHandler | None = None

    def set_handler(self, handler: MessageHandler):
        self._handler = handler

    async def _on_message(self, msg: InboundMessage) -> OutboundMessage:
        if self._handler is None:
            return OutboundMessage(
                text="内部错误：handler 未注册",
                channel=self.name,
                chat_id=msg.chat_id,
                session_id=msg.session_id,
            )
        return await self._handler(msg)

    @abstractmethod
    async def start(self):
        """启动渠道（阻塞式运行）"""
        ...

    @abstractmethod
    async def send(self, msg: OutboundMessage):
        """发送消息到外部平台"""
        ...
