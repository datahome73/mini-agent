"""
入口 — python main.py [cli|telegram]
"""

import argparse
import asyncio
import logging
import sys

from config import Config
from bus import InboundMessage, OutboundMessage

from provider.deepseek import DeepSeekProvider
from tools.registry import ToolRegistry
from tools.filesystem import init_sandbox, read_file_tool, write_file_tool, search_tool
from tools.web import web_fetch_tool, web_search_tool
from tools.shell import shell_tool
from tools.memory_tool import init as init_memory_tools, read_memory_tool, remember_tool
from memory.session import SessionMemory
from memory.long_term import LongTermMemory
from cron.scheduler import CronScheduler, CronJob, parse_interval
from agent_core import AgentCore

from channels.cli import CLIChannel
from channels.telegram import TelegramChannel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_agent(cfg: Config) -> AgentCore:
    """组装 Agent 核心"""
    provider = DeepSeekProvider(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        model=cfg.model,
    )

    init_sandbox(cfg.workspace_dir)

    registry = ToolRegistry()
    registry.register(read_memory_tool)
    registry.register(remember_tool)
    registry.register(read_file_tool)
    registry.register(write_file_tool)
    registry.register(search_tool)
    registry.register(web_fetch_tool)
    registry.register(web_search_tool)
    registry.register(shell_tool)

    session_memory = SessionMemory(cfg.workspace_dir)
    long_term_memory = LongTermMemory(cfg.workspace_dir)

    init_memory_tools(long_term_memory)

    agent = AgentCore(
        provider=provider,
        tool_registry=registry,
        session_memory=session_memory,
        long_term_memory=long_term_memory,
        max_tool_iterations=cfg.max_tool_iterations,
        session_history_size=cfg.session_history_size,
    )
    return agent


async def run_cli(cfg: Config):
    """CLI 模式 — 流式输出"""
    agent = build_agent(cfg)
    channel = CLIChannel(agent=agent)

    if cfg.cron_enabled:
        scheduler = CronScheduler(agent, channel)
        scheduler.add_job(CronJob(
            name="heartbeat",
            interval_sec=parse_interval(cfg.cron_interval),
            prompt=cfg.cron_prompt,
            chat_id=cfg.cron_chat_id,
        ))
        asyncio.create_task(scheduler.run())

    await channel.start()


async def run_telegram(cfg: Config):
    """Telegram 模式 — 流式输出（编辑消息模拟打字机）"""
    agent = build_agent(cfg)
    channel = TelegramChannel(token=cfg.telegram_token, agent=agent)

    if cfg.cron_enabled:
        scheduler = CronScheduler(agent, channel)
        scheduler.add_job(CronJob(
            name="heartbeat",
            interval_sec=parse_interval(cfg.cron_interval),
            prompt=cfg.cron_prompt,
            chat_id=cfg.cron_chat_id,
        ))
        asyncio.create_task(scheduler.run())

    await channel.start()


def main():
    parser = argparse.ArgumentParser(description="🐈 南欧迷你 Agent")
    parser.add_argument(
        "mode",
        nargs="?",
        default="cli",
        choices=["cli", "telegram"],
        help="运行模式（默认 cli）",
    )
    args = parser.parse_args()

    cfg = Config.from_env()

    if args.mode == "telegram":
        errors = cfg.validate()
        if errors:
            for e in errors:
                print(f"✗ {e}")
            sys.exit(1)

    print(f"🐈 南欧迷你 Agent — {args.mode} 模式")
    print(f"   模型: {cfg.model}")
    print(f"   工作空间: {cfg.workspace_dir}")

    if args.mode == "cli":
        asyncio.run(run_cli(cfg))
    else:
        asyncio.run(run_telegram(cfg))


if __name__ == "__main__":
    main()
