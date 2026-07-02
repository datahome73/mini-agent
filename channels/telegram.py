"""
Telegram 渠道 — 长轮询模式。
通过 python-telegram-bot 接收和发送消息。
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, filters

from channels.base import BaseChannel
from bus import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    """Telegram Bot 渠道"""

    def __init__(self, token: str):
        super().__init__("telegram")
        self._token = token
        self._app: Application | None = None
        self._stop_event = asyncio.Event()

    async def start(self):
        """启动 Bot（长轮询）"""
        self._app = Application.builder().token(self._token).build()
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_update))
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(allowed_updates=["messages"])
        logger.info("Telegram channel started, polling...")
        await self._stop_event.wait()

    async def stop(self):
        """停止 Bot"""
        self._stop_event.set()
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def _handle_update(self, update: Update, _context):
        """Telegram 回调 — 收到消息后的处理"""
        if not update.message or not update.message.text:
            return

        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id) if update.effective_user else chat_id
        session_id = f"telegram:{chat_id}:{user_id}"

        inbound = InboundMessage(
            channel="telegram",
            text=update.message.text,
            session_id=session_id,
            chat_id=chat_id,
            raw=update,
        )

        outbound = await self._on_message(inbound)
        await update.message.reply_text(outbound.text)

    async def send(self, msg: OutboundMessage):
        """主动发送（不在回复上下文中时使用）"""
        if self._app and msg.chat_id:
            await self._app.bot.send_message(chat_id=msg.chat_id, text=msg.text)
