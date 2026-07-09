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


async def learn_skill(url: str, name: str | None = None) -> str:
    """从 URL 下载一个 .md 技能文档并保存到 skills/ 目录。

    Args:
        url: 技能文档的下载链接
        name: 可选，技能名称（不含 .md）。不传则从 URL 自动推导。
    """
    if _SKILLS_DIR is None:
        return "错误：Skill 系统未初始化"

    # 下载
    try:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.text
    except Exception as e:
        return f"下载失败：{e}"

    if not content.strip():
        return "错误：下载的内容为空"

    # 确定文件名
    if name:
        safe_name = name.replace("..", "").replace("/", "").replace("\\", "")
    else:
        # 从 URL 文件名或 frontmatter 的 name 字段推导
        import re
        m = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        if m:
            safe_name = m.group(1).strip()
        else:
            base = url.rstrip("/").split("/")[-1]
            safe_name = base.replace(".md", "").replace("..", "")

    safe_name = safe_name.replace(" ", "-").replace("..", "").replace("/", "")
    path = os.path.join(_SKILLS_DIR, f"{safe_name}.md")

    # 写入
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return f"写入技能文件失败：{e}"

    return f"✓ 已学习新技能 '{safe_name}'（{len(content)} 字符）\n路径：{path}"


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

learn_skill_tool = Tool(
    name="learn_skill",
    description="从 URL 下载一个 .md 技能文档并保存到 skills/ 目录。通过此工具可以从网络学习新能力。参数 name 可选，不传则自动从 URL 或文档内容推断。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "技能 .md 文件的下载链接"},
            "name": {"type": "string", "description": "可选，技能名称（不含 .md）"},
        },
        "required": ["url"],
    },
    fn=learn_skill,
)
