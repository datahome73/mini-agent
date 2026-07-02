"""
长期记忆 — 类似 MEMORY.md 的持久化方式。
Agent 可以通过 `remember` / `read_memory` 工具读写它，构成长期事实库。
"""

from pathlib import Path


DEFAULT_MEMORY = """# 长期记忆

这是南欧 🐈 的长期记忆文件。
重要的用户信息和项目事实会被记录在这里。
"""


class LongTermMemory:
    """长期记忆管理"""

    def __init__(self, workspace_dir: str):
        self._path = Path(workspace_dir) / "memory.md"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text(DEFAULT_MEMORY, encoding="utf-8")

    def load(self) -> str:
        """读取当前长期记忆"""
        try:
            return self._path.read_text(encoding="utf-8")
        except Exception:
            return DEFAULT_MEMORY

    def append(self, fact: str) -> str:
        """追加一条事实记录"""
        try:
            current = self.load().rstrip() + "\n"
            current += f"- {fact}\n"
            self._path.write_text(current, encoding="utf-8")
            return f"✓ 已追加事实：{fact}"
        except Exception as e:
            return f"写入失败：{e}"

    def update(self, content: str) -> str:
        """覆盖更新长期记忆"""
        try:
            self._path.write_text(content, encoding="utf-8")
            return f"✓ 长期记忆已更新（{len(content)} 字符）"
        except Exception as e:
            return f"更新失败：{e}"

    def path(self) -> str:
        return str(self._path)
