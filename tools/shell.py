"""
Shell 工具 — 执行命令。
带有基础的安全沙箱：只允许特定命令。
"""

import asyncio
import logging
import shlex

from tools.base import Tool

logger = logging.getLogger(__name__)

# 允许的命令前缀（白名单）
ALLOWED_COMMANDS = [
    "ls", "cat", "head", "tail", "wc", "find", "grep",
    "pwd", "echo", "date", "whoami", "uname",
    "python3", "python", "pip3", "pip",
    "mkdir", "cp", "mv", "rm",
    "cd", "pwd",
    "du", "df", "sort", "uniq",
]

# 明确禁止的命令片段
BLOCKED_PATTERNS = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if",
    "sudo", "chmod 777", "chown",
    ":(){ :|:& };:",  # fork bomb
    ">/dev/sda", ">/dev/null",
]


async def run_command(command: str, timeout: int = 30) -> str:
    """执行 shell 命令并返回输出"""
    # 安全检查
    cmd_lower = command.lower().strip()

    for pattern in BLOCKED_PATTERNS:
        if pattern in cmd_lower:
            return f"错误：命令中包含禁止的操作（{pattern}）"

    cmd_name = shlex.split(command)[0]
    if cmd_name not in ALLOWED_COMMANDS:
        return f"错误：命令 '{cmd_name}' 不在允许列表中。允许的命令：{', '.join(ALLOWED_COMMANDS)}"

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = ""
        if stdout:
            output += stdout.decode("utf-8", errors="replace")
        if stderr:
            output += "\n[stderr]\n" + stderr.decode("utf-8", errors="replace")
        if len(output) > 5000:
            output = output[:5000] + "\n\n... (输出已截断)"
        return output.strip() or "(命令无输出)"
    except asyncio.TimeoutError:
        return f"错误：命令执行超时（{timeout}秒）"
    except Exception as e:
        return f"错误：{e}"


# ===== 注册 =====
shell_tool = Tool(
    name="run_command",
    description="执行 shell 命令。仅限白名单命令。timeout 为超时秒数。",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的命令"},
            "timeout": {"type": "integer", "description": "超时秒数（默认 30）"},
        },
        "required": ["command"],
    },
    fn=run_command,
    requires_confirmation=True,
)
