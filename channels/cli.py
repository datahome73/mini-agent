"""
CLI 渠道 — 终端交互模式。
适合在 Docker 中 `docker run -it` 使用。
"""

import asyncio
import sys

from channels.base import BaseChannel
from bus import InboundMessage, OutboundMessage


class CLIChannel(BaseChannel):
    """终端交互渠道"""

    def __init__(self):
        super().__init__("cli")

    async def start(self):
        """阻塞式运行，从 stdin 读消息，发到 stdout"""
        print("🐈 南欧迷你 Agent — CLI 模式")
        print("输入你的消息，输入 /quit 退出\n")

        while True:
            try:
                text = input("你 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break

            if not text:
                continue
            if text == "/quit":
                print("再见！")
                break

            inbound = InboundMessage(
                channel="cli",
                text=text,
                session_id="cli-default",
            )

            outbound = await self._on_message(inbound)
            print(f"\n🐈 {outbound.text}\n")

    async def send(self, msg: OutboundMessage):
        """CLI 模式下由 start 直接输出，此方法备用"""
        print(f"\n🐈 {msg.text}\n")
