"""
长期记忆 — 类似 MEMORY.md 的持久化方式。
Agent 可以通过 `remember` / `read_memory` 工具读写它，构成长期事实库。
身份文件 identity.md 存放角色设定和行为规范，与事实记忆分开管理。
"""

from pathlib import Path


DEFAULT_MEMORY = """# 长期记忆

这是迷因 🐈 的长期记忆文件。
重要的用户信息和项目事实会被记录在这里。
"""

DEFAULT_IDENTITY = """# 🧬 角色身份

你是迷因 🐈，一个极简的个人 AI 助手。

## 核心原则
- 用简洁的中文回答
- 不清楚的就说不知道，不要编造

## 工具使用
- 各工具按 JSON Schema 传入参数即可
- 工具返回错误时，先检查参数再重试
- 工具结果自动回塞上下文，无需手动记录

## 记忆
- 长期记忆通过 `remember` / `read_memory` 工具管理
- 用户说"请记住"时必须立即调用 remember 工具
- 会话开始时自动加载了记忆，不需要复述
"""


class LongTermMemory:
    """长期记忆管理"""

    def __init__(self, workspace_dir: str):
        self._workspace = Path(workspace_dir)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._path = self._workspace / "memory.md"
        self._identity_path = self._workspace / "identity.md"
        if not self._path.exists():
            self._path.write_text(DEFAULT_MEMORY, encoding="utf-8")
        if not self._identity_path.exists():
            self._identity_path.write_text(DEFAULT_IDENTITY, encoding="utf-8")

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

    def load_identity(self) -> str:
        """读取角色身份和系统行为规范"""
        try:
            return self._identity_path.read_text(encoding="utf-8")
        except Exception:
            return DEFAULT_IDENTITY

    def update_identity(self, content: str) -> str:
        """覆盖更新角色身份"""
        try:
            self._identity_path.write_text(content, encoding="utf-8")
            return f"✓ 角色身份已更新（{len(content)} 字符）"
        except Exception as e:
            return f"更新失败：{e}"
