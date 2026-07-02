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
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"

    # Telegram (可选)
    telegram_token: str = ""

    # 工作空间
    workspace_dir: str = "/app/data"

    # Agent 行为
    max_tool_iterations: int = 10
    session_history_size: int = 20

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            telegram_token=os.environ.get("TELEGRAM_TOKEN", ""),
            workspace_dir=os.environ.get("WORKSPACE_DIR", "/app/data"),
            max_tool_iterations=int(os.environ.get("MAX_TOOL_ITERATIONS", "10")),
            session_history_size=int(os.environ.get("SESSION_HISTORY_SIZE", "20")),
        )

    def validate(self):
        errors = []
        if not self.api_key:
            errors.append("DEEPSEEK_API_KEY 未设置")
        if not self.telegram_token:
            errors.append("TELEGRAM_TOKEN 未设置（Telegram 模式需要）")
        return errors
