"""
记忆工具 — 让 Agent 可以主动读写长期记忆。
"""

from tools.base import Tool
from memory.long_term import LongTermMemory

_ltm: LongTermMemory | None = None


def init(memory: LongTermMemory):
    global _ltm
    _ltm = memory


async def read_memory() -> str:
    """读取长期记忆文件的内容"""
    if _ltm is None:
        return "错误：记忆模块未初始化"
    return _ltm.load()


async def remember(fact: str) -> str:
    """记住一条新的事实，追加到长期记忆。"""
    if _ltm is None:
        return "错误：记忆模块未初始化"
    result = _ltm.append(fact)
    if result.startswith("✓"):
        return f"已记住：{fact}"
    return result


# ===== 注册工具 =====
read_memory_tool = Tool(
    name="read_memory",
    description="读取长期记忆文件，获取已保存的用户信息和项目事实。",
    parameters={
        "type": "object",
        "properties": {},
    },
    fn=read_memory,
)

remember_tool = Tool(
    name="remember",
    description="记住一条新的事实。把重要信息（用户偏好、关键决定、项目事实等）追加到长期记忆。当用户说'请记住'时必须调用此工具。",
    parameters={
        "type": "object",
        "properties": {
            "fact": {"type": "string", "description": "要记住的事实内容"},
        },
        "required": ["fact"],
    },
    fn=remember,
)
