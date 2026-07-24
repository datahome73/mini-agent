"""
文件系统工具 — 读文件、写文件、搜索文件内容。
路径统一通过 WorkspaceSandbox 进行安全解析。
"""

import os
import re
from pathlib import Path

from tools.base import Tool
from security.workspace import WorkspaceSandbox

# 工作空间沙箱（在 main.py 初始化时设置）
_sandbox: WorkspaceSandbox | None = None


def init_sandbox(workspace_dir: str):
    global _sandbox
    _sandbox = WorkspaceSandbox(workspace_dir)


def _resolve(path: str) -> str | None:
    """通过沙箱解析路径，越界返回 None"""
    if _sandbox is None:
        return None
    p = _sandbox.resolve(path)
    return str(p) if p else None


async def read_file(path: str) -> str:
    """读取文件内容"""
    full = _resolve(path)
    if full is None:
        return "错误：路径不在允许的工作空间内"
    if not os.path.isfile(full):
        return f"错误：文件不存在: {path}"
    try:
        with open(full, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取失败：{e}"


async def write_file(path: str, content: str) -> str:
    """写入文件"""
    full = _resolve(path)
    if full is None:
        return "错误：路径不在允许的工作空间内"
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✓ 已写入 {path}（{len(content)} 字符）"
    except Exception as e:
        return f"写入失败：{e}"


async def search(pattern: str, path: str = ".") -> str:
    """在文件内容中搜索文本"""
    full = _resolve(path)
    if full is None:
        return "错误：路径不在允许的工作空间内"
    if not os.path.isdir(full):
        return f"错误：目录不存在: {path}"

    results = []
    try:
        for root, _, files in os.walk(full):
            for f in files:
                if f.startswith("."):
                    continue
                fp = os.path.join(root, f)
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        for i, line in enumerate(fh, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                rel = os.path.relpath(fp, _sandbox.root)
                                results.append(f"{rel}:{i}: {line.rstrip()[:200]}")
                                if len(results) >= 30:
                                    break
                except Exception:
                    continue
            if len(results) >= 30:
                break
    except Exception as e:
        return f"搜索失败：{e}"

    if not results:
        return "未找到匹配内容"
    return "\n".join(results[:30])


# ===== 注册工具 =====
read_file_tool = Tool(
    name="read_file",
    description="读取指定路径的文件内容。path 相对于工作空间根目录。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径，相对于工作空间"},
        },
        "required": ["path"],
    },
    fn=read_file,
)

write_file_tool = Tool(
    name="write_file",
    description="写入内容到指定路径的文件。path 相对于工作空间根目录。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径，相对于工作空间"},
            "content": {"type": "string", "description": "要写入的文件内容"},
        },
        "required": ["path", "content"],
    },
    fn=write_file,
    requires_confirmation=True,
)

search_tool = Tool(
    name="search",
    description="在文件中搜索文本内容（支持正则表达式）。path 是搜索的目录。",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "搜索关键词或正则"},
            "path": {"type": "string", "description": "搜索目录路径，默认 '.'"},
        },
        "required": ["pattern"],
    },
    fn=search,
)
