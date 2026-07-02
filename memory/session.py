"""
会话记忆 — JSONL 持久化。
每条消息按 session_id 分文件存储。
"""

import json
import os
from pathlib import Path


class SessionMemory:
    """对话历史存储"""

    def __init__(self, workspace_dir: str):
        self._sessions_dir = Path(workspace_dir) / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        """会话文件路径，确保文件名安全"""
        safe = session_id.replace(":", "_").replace("/", "_")
        return self._sessions_dir / f"{safe}.jsonl"

    def append(self, session_id: str, role: str, content: str):
        """追加一条消息到会话"""
        path = self._session_path(session_id)
        entry = {"role": role, "content": content}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_recent(self, session_id: str, n: int = 20) -> list[dict]:
        """获取最近 N 条会话消息"""
        path = self._session_path(session_id)
        if not path.exists():
            return []

        lines = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            return []

        return lines[-n:]

    def clear(self, session_id: str):
        """清空会话"""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()

    def list_sessions(self) -> list[str]:
        """列出所有会话 ID"""
        sessions = []
        for f in self._sessions_dir.glob("*.jsonl"):
            # 反解回原始 session_id
            name = f.stem
            # 简单反解（工具方法，不保证完全还原）
            sessions.append(name)
        return sessions
