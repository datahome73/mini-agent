"""
工作空间安全 — 路径沙箱。
确保工具访问不越界。
"""

from pathlib import Path


class WorkspaceSandbox:
    """工作空间路径沙箱"""

    def __init__(self, workspace_dir: str):
        self._root = Path(workspace_dir).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, relative_path: str) -> Path | None:
        """解析相对路径，如果越界则返回 None"""
        try:
            full = (self._root / relative_path).resolve()
            if str(full).startswith(str(self._root)):
                return full
            return None
        except Exception:
            return None

    def ensure_dir(self, *parts: str) -> Path:
        """确保子目录存在"""
        path = self._root.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path
