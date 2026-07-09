"""
Skill 工具 — 让 Agent 能读取 skills/ 目录下的 .md 技能文档。
通过加载 skill，Agent 可以学会新能力，而不需要改代码。
"""
import os
import logging
from pathlib import Path

from tools.base import Tool

logger = logging.getLogger(__name__)

_SKILLS_DIR: str | None = None


def init(skills_dir: str):
    """初始化 skills 目录路径（在 main.py 中调用）"""
    global _SKILLS_DIR
    _SKILLS_DIR = skills_dir
    # 确保目录存在
    Path(skills_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Skills 目录: %s", skills_dir)


async def load_skill(name: str) -> str:
    """读取一个技能文档，学会新能力。技能是 .md 文件，包含步骤和指令。"""
    if _SKILLS_DIR is None:
        return "错误：Skill 系统未初始化"

    # 简单的安全过滤：防止路径穿越
    safe = name.replace("..", "").replace("/", "").replace("\\", "")
    path = os.path.join(_SKILLS_DIR, f"{safe}.md")

    if not os.path.isfile(path):
        available = _list_skills()
        msg = f"技能 '{name}' 不存在。"
        if available:
            msg += f"\n可用技能：\n" + "\n".join(f"  - {s}" for s in available)
        else:
            msg += "\n暂无可用技能。"
        return msg

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取技能失败：{e}"


async def list_skills() -> str:
    """列出所有可用的技能文档。"""
    if _SKILLS_DIR is None:
        return "错误：Skill 系统未初始化"

    available = _list_skills()
    if not available:
        return "暂无可用技能。"
    return "可用技能：\n" + "\n".join(f"  - {s}" for s in available)


def _list_skills() -> list[str]:
    """扫描 skills/ 目录下的 .md 文件"""
    try:
        files = sorted(os.listdir(_SKILLS_DIR))
        return sorted(
            f.replace(".md", "")
            for f in files
            if f.endswith(".md")
        )
    except FileNotFoundError:
        return []


# ===== 注册工具 =====
load_skill_tool = Tool(
    name="load_skill",
    description="读取一个技能文档（.md 文件），学习新能力。遇到不熟悉的任务时，先调用此工具查看是否有对应技能。参数 name 是技能名称，不加 .md 后缀。",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "技能名称，例如 'joke-teller'",
            },
        },
        "required": ["name"],
    },
    fn=load_skill,
)

list_skills_tool = Tool(
    name="list_skills",
    description="列出所有可用的技能文档，方便了解当前已安装的能力。",
    parameters={
        "type": "object",
        "properties": {},
    },
    fn=list_skills,
)
