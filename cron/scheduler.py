"""
定时任务调度器 — 作为 asyncio task 与 channel 并行运行。

用法
----
scheduler = CronScheduler(agent, channel)
scheduler.add_job(CronJob(name="心跳", interval_sec=86400, prompt="检查状态", chat_id="123"))
asyncio.create_task(scheduler.run())
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from bus import InboundMessage

logger = logging.getLogger(__name__)


def parse_interval(text: str) -> int:
    """将人类可读间隔转为秒。

    支持格式:
        "30"   -> 30 秒
        "30s"  -> 30 秒
        "5m"   -> 300 秒
        "2h"   -> 7200 秒
        "1d"   -> 86400 秒
    """
    text = text.strip().lower()
    if text.endswith("d"):
        return int(text[:-1]) * 86400
    if text.endswith("h"):
        return int(text[:-1]) * 3600
    if text.endswith("m"):
        return int(text[:-1]) * 60
    if text.endswith("s"):
        return int(text[:-1])
    return int(text)


@dataclass
class CronJob:
    """单个定时任务定义"""

    name: str
    interval_sec: int
    prompt: str  # 每 tick 发给 agent 的提示词
    chat_id: Optional[str] = None  # None = 只记日志，不投递


class CronScheduler:
    """定时任务调度器"""

    def __init__(self, agent, channel, session_id: str = "cron-default"):
        self._agent = agent
        self._channel = channel
        self._session_id = session_id
        self._jobs: list[CronJob] = []
        self._tasks: list[asyncio.Task] = []

    # -- 公开接口 --

    def add_job(self, job: CronJob):
        """注册一个定时任务（启动前调用）"""
        self._jobs.append(job)

    async def run(self):
        """启动所有已注册的定时任务（非阻塞）"""
        for job in self._jobs:
            task = asyncio.create_task(
                self._job_loop(job), name=f"cron:{job.name}"
            )
            self._tasks.append(task)
        logger.info("CronScheduler 已启动，共 %d 个任务", len(self._jobs))

    # -- 内部 --

    async def _job_loop(self, job: CronJob):
        """单个任务的循环体"""
        await asyncio.sleep(job.interval_sec)  # 首次不立即执行
        while True:
            try:
                await self._execute(job)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("[cron:%s] 执行异常: %s", job.name, e)
            await asyncio.sleep(job.interval_sec)

    async def _execute(self, job: CronJob):
        """构造消息 -> agent 处理 -> channel 投递"""
        msg = InboundMessage(
            channel="cron",
            text=job.prompt,
            session_id=self._session_id,
            chat_id=job.chat_id,
        )
        reply = await self._agent.process_message(msg)

        if job.chat_id and self._channel:
            await self._channel.send(reply)
        else:
            logger.info("[cron:%s] 回复: %s", job.name, reply.text[:200])
