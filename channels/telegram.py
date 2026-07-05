"""Telegram 渠道 — 长轮询模式。
通过 python-telegram-bot 接收和发送消息。
支持流式输出（编辑消息实现打字机效果）。"""

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, MessageHandler, filters

from channels.base import BaseChannel
from bus import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)

_STREAM_EDIT_INTERVAL = 0.4


class TelegramChannel(BaseChannel):
    """Telegram Bot 渠道"""

    def __init__(self, token: str, agent=None):
        super().__init__("telegram")
        self._token = token
        self._agent = agent
        self._app: Application | None = None
        self._stop_event = asyncio.Event()

    async def start(self):
        self._app = Application.builder().token(self._token).build()
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_update)
        )
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(allowed_updates=["messages"])
        logger.info("Telegram channel started, polling...")
        await self._stop_event.wait()

    async def stop(self):
        self._stop_event.set()
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def _handle_update(self, update: Update, _context):
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

        if self._agent:
            await self._handle_streaming(update, inbound)
        else:
            outbound = await self._on_message(inbound)
            await update.message.reply_text(outbound.text)

    async def _handle_streaming(self, update: Update, inbound: InboundMessage):
        try:
            await update.effective_chat.send_action(action=ChatAction.TYPING)
        except Exception:
            pass

        full_text = ""
        try:
            sent = await update.message.reply_text("...")
            last_edit = 0.0

            async for chunk in self._agent.process_message_stream(inbound):
                full_text += chunk
                now = asyncio.get_event_loop().time()
                if now - last_edit >= _STREAM_EDIT_INTERVAL:
                    try:
                        await sent.edit_text(full_text)
                    except Exception:
                        pass
                    last_edit = now

            if full_text:
                try:
                    await sent.edit_text(full_text)
                except Exception:
                    pass
            else:
                await sent.edit_text("(空回复)")

        except Exception as e:
            logger.exception("流式处理 TG 消息异常")
            try:
                await update.message.reply_text(f"内部错误：{e}")
            except Exception:
                pass

    async def send(self, msg: OutboundMessage):
        if self._app and msg.chat_id:
            await self._app.bot.send_message(chat_id=msg.chat_id, text=msg.text)
