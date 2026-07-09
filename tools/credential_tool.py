"""
凭证管理工具 — 安全存储 API Key、Token 等敏感信息。
存为 <WORKSPACE_DIR>/credentials.json，避免污染长期记忆。
"""
import json
import logging
import os
from pathlib import Path

from tools.base import Tool

logger = logging.getLogger(__name__)

_CREDS_PATH: str | None = None


def init(workspace_dir: str):
    """初始化凭证文件路径（在 main.py 中调用）"""
    global _CREDS_PATH
    _CREDS_PATH = os.path.join(workspace_dir, "credentials.json")
    logger.info("凭证文件: %s", _CREDS_PATH)


def _load_all() -> dict[str, str]:
    """读取所有凭证"""
    if _CREDS_PATH is None or not os.path.isfile(_CREDS_PATH):
        return {}
    try:
        with open(_CREDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data: dict[str, str]) -> str:
    """覆写凭证文件"""
    if _CREDS_PATH is None:
        return "错误：凭证系统未初始化"
    try:
        Path(_CREDS_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(_CREDS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return f"✓ 已保存 {len(data)} 条凭证"
    except Exception as e:
        return f"写入凭证失败：{e}"


async def save_credential(name: str, value: str) -> str:
    """保存一条凭证（API Key、Token 等）。如果同名已存在则覆盖。"""
    data = _load_all()
    data[name] = value
    return _save_all(data)


async def get_credential(name: str) -> str:
    """读取一条凭证的值。"""
    data = _load_all()
    val = data.get(name)
    if val is None:
        keys = list(data.keys())
        msg = f"凭证 '{name}' 不存在。"
        if keys:
            msg += f"\n已有凭证：{', '.join(keys)}"
        else:
            msg += "\n暂无凭证。"
        return msg
    return val


async def list_credentials() -> str:
    """列出所有已保存的凭证名称（不显示值）。"""
    data = _load_all()
    if not data:
        return "暂无凭证。"
    lines = [f"   {i+1}. {k}" for i, k in enumerate(data.keys())]
    return f"已保存 {len(data)} 条凭证：\n" + "\n".join(lines)


async def delete_credential(name: str) -> str:
    """删除一条凭证。"""
    data = _load_all()
    if name not in data:
        return f"凭证 '{name}' 不存在。"
    del data[name]
    return _save_all(data)


# ===== 注册工具 =====
save_credential_tool = Tool(
    name="save_credential",
    description="保存一条凭证（API Key、Token、密码等敏感信息）到安全的本地文件。同名会自动覆盖。收到密钥信息时优先用此工具，不要记在长期记忆里。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "凭证名称，例如 'meyo_api_key'"},
            "value": {"type": "string", "description": "凭证值，例如 'sk_xxx'"},
        },
        "required": ["name", "value"],
    },
    fn=save_credential,
)

get_credential_tool = Tool(
    name="get_credential",
    description="读取一条已保存的凭证的值。用于获取 API Key 等敏感信息以调用外部服务。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "凭证名称"},
        },
        "required": ["name"],
    },
    fn=get_credential,
)

list_credentials_tool = Tool(
    name="list_credentials",
    description="列出所有已保存的凭证名称（不显示值）。",
    parameters={
        "type": "object",
        "properties": {},
    },
    fn=list_credentials,
)

delete_credential_tool = Tool(
    name="delete_credential",
    description="删除一条已保存的凭证。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "要删除的凭证名称"},
        },
        "required": ["name"],
    },
    fn=delete_credential,
)
