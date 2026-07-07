"""CLI 渠道 — 终端交互模式。
适合在 Docker 中 `docker run -it` 使用。"""

import asyncio
import sys

from channels.base import BaseChannel
from bus import InboundMessage, OutboundMessage


class CLIChannel(BaseChannel):
    """终端交互渠道"""

    def __init__(self, agent=None):
        super().__init__("cli")
        self.agent = agent

    async def start(self):
        """阻塞式运行，从 stdin 读消息，发到 stdout"""
        mode_label = "流式" if self.agent else "非流式"
        print(f"🐈 南欧迷你 Agent — CLI 模式（{mode_label}）")
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
            if text == "/trace":
                if self.agent:
                    print("\n" + self.agent.format_last_trace("cli-default") + "\n")
                else:
                    print("\nAgent 未启用，无法查看 trace。\n")
                continue

            inbound = InboundMessage(
                channel="cli",
                text=text,
                session_id="cli-default",
            )

            if self.agent:
                print("🐈 ", end="", flush=True)
                async for chunk in self.agent.process_message_stream(inbound):
                    print(chunk, end="", flush=True)
                print("\n")
            else:
                outbound = await self._on_message(inbound)
                print(f"\n🐈 {outbound.text}\n")

    async def send(self, msg: OutboundMessage):
        print(f"\n🐈 {msg.text}\n")
