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
from tools.http import http_request_tool
from tools.memory_tool import init as init_memory_tools, read_memory_tool, remember_tool
from tools.skill import init as init_skill_tools, load_skill_tool, list_skills_tool, learn_skill_tool
from tools.credential_tool import (
    init as init_credential_tools,
    save_credential_tool,
    get_credential_tool,
    list_credentials_tool,
    delete_credential_tool,
)
from tools.plan import (
    create_plan_tool,
    complete_step_tool,
    revise_plan_tool,
    get_plan_tool,
    init_plan_tools,
)
from tools.mcp_tool import build_mcp_tools
from tools.confirm import ConfirmManager
from mcp_client.manager import MCPManager
from memory.session import SessionMemory
from memory.long_term import LongTermMemory
from memory.trace import TraceStore
from memory.context_manager import ContextManager, ContextConfig
from cron.scheduler import CronScheduler, CronJob, parse_interval
from plugin_loader import PluginLoader
from agent_core import AgentCore

from channels.cli import CLIChannel
from channels.telegram import TelegramChannel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_agent(cfg: Config, mcp_manager: MCPManager | None = None) -> AgentCore:
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
    registry.register(http_request_tool)
    registry.register(load_skill_tool)
    registry.register(list_skills_tool)
    registry.register(learn_skill_tool)
    registry.register(save_credential_tool)
    registry.register(get_credential_tool)
    registry.register(list_credentials_tool)
    registry.register(delete_credential_tool)
    registry.register(create_plan_tool)
    registry.register(complete_step_tool)
    registry.register(revise_plan_tool)
    registry.register(get_plan_tool)

    session_memory = SessionMemory(cfg.workspace_dir)
    long_term_memory = LongTermMemory(cfg.workspace_dir)
    trace_store = TraceStore(cfg.workspace_dir)

    init_memory_tools(long_term_memory)
    init_skill_tools("skills")
    init_credential_tools(cfg.workspace_dir)
    init_plan_tools()

    # 加载第三方插件
    context = {
        'workspace_dir': cfg.workspace_dir,
        'agent_config': {
            'model': cfg.model,
            'max_tool_iterations': cfg.max_tool_iterations,
            'session_history_size': cfg.session_history_size,
        },
    }
    if long_term_memory is not None:
        context['long_term_memory'] = long_term_memory
    plugin_loader = PluginLoader(plugins_dir='plugins')
    loaded_plugins = plugin_loader.load_all(registry, context)
    if loaded_plugins:
        logger.info('共加载 %d 个插件', len(loaded_plugins))
        for p in loaded_plugins:
            logger.info('  ✓ %s: %s', p.name, p.description)

    # 注册 MCP 工具（如果有）
    if mcp_manager and mcp_manager._active_tools:
        for t in build_mcp_tools(mcp_manager):
            registry.register(t)
            logger.info('  ✓ MCP %s', t.name)

    context_config = ContextConfig(
        max_total_tokens=cfg.context_max_total_tokens,
        system_max_tokens=cfg.context_system_max_tokens,
        tools_max_tokens=cfg.context_tools_max_tokens,
        history_max_tokens=cfg.context_history_max_tokens,
        min_history_messages=cfg.context_min_history_messages,
        max_history_messages=cfg.context_max_history_messages,
    )
    context_manager = ContextManager(config=context_config)
    confirm_manager = ConfirmManager()

    agent = AgentCore(
        provider=provider,
        tool_registry=registry,
        session_memory=session_memory,
        long_term_memory=long_term_memory,
        confirm_manager=confirm_manager,
        trace_store=trace_store,
        context_manager=context_manager,
        max_tool_iterations=cfg.max_tool_iterations,
        session_history_size=cfg.session_history_size,
    )
    return agent


async def run_cli(cfg: Config):
    """CLI 模式 — 流式输出"""
    mcp_manager = MCPManager(config_path=cfg.mcp_config_path)
    await mcp_manager.load_all()
    agent = build_agent(cfg, mcp_manager=mcp_manager)
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
    await mcp_manager.shutdown()


async def run_telegram(cfg: Config):
    """Telegram 模式 — 流式输出（编辑消息模拟打字机）"""
    mcp_manager = MCPManager(config_path=cfg.mcp_config_path)
    await mcp_manager.load_all()
    agent = build_agent(cfg, mcp_manager=mcp_manager)
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
    await mcp_manager.shutdown()


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
