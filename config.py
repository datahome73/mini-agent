"""
配置管理 — 从环境变量加载。
在 Docker 中运行时，通过 -e KEY=VALUE 传入。
"""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # DeepSeek
    api_key: str = ""
    base_url: str = "https://api.datahome73.com/v1"
    model: str = "deepseek-v4-flash"

    # Telegram (可选)
    telegram_token: str = ""

    # 工作空间
    workspace_dir: str = "/app/data"

    # Agent 行为
    max_tool_iterations: int = 10
    session_history_size: int = 20

    # 上下文窗口预算（Token 管理）
    context_max_total_tokens: int = 32768
    context_system_max_tokens: int = 4096
    context_tools_max_tokens: int = 4096
    context_history_max_tokens: int = 24576
    context_min_history_messages: int = 2
    context_max_history_messages: int = 100

    # Cron 定时任务
    cron_enabled: bool = False
    cron_interval: str = "1d"
    cron_prompt: str = "心跳检测：回复当前状态和一句'我还活着'"
    cron_chat_id: str = ""

    # MCP 配置
    mcp_config_path: str = "mcp_client/servers.json"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.datahome73.com/v1"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            telegram_token=os.environ.get("TELEGRAM_TOKEN", ""),
            workspace_dir=os.environ.get("WORKSPACE_DIR", "/app/data"),
            max_tool_iterations=int(os.environ.get("MAX_TOOL_ITERATIONS", "10")),
            session_history_size=int(os.environ.get("SESSION_HISTORY_SIZE", "20")),
            context_max_total_tokens=int(os.environ.get("CONTEXT_MAX_TOKENS", "32768")),
            context_system_max_tokens=int(os.environ.get("CONTEXT_SYSTEM_MAX_TOKENS", "4096")),
            context_tools_max_tokens=int(os.environ.get("CONTEXT_TOOLS_MAX_TOKENS", "4096")),
            context_history_max_tokens=int(os.environ.get("CONTEXT_HISTORY_MAX_TOKENS", "24576")),
            context_min_history_messages=int(os.environ.get("CONTEXT_MIN_HISTORY", "2")),
            context_max_history_messages=int(os.environ.get("CONTEXT_MAX_HISTORY", "100")),
            cron_enabled=os.environ.get("CRON_ENABLED", "").lower() in ("1", "true", "yes"),
            cron_interval=os.environ.get("CRON_INTERVAL", "1d"),
            cron_prompt=os.environ.get("CRON_PROMPT", "心跳检测：回复当前状态和一句'我还活着'"),
            cron_chat_id=os.environ.get("CRON_CHAT_ID", ""),
        )

    def validate(self):
        errors = []
        if not self.api_key:
            errors.append("DEEPSEEK_API_KEY 未设置")
        if not self.telegram_token:
            errors.append("TELEGRAM_TOKEN 未设置（Telegram 模式需要）")
        return errors
