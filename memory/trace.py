"""Agent run traces.

TraceStore keeps the latest execution trace per session and also writes a
timestamped JSON file for later debugging.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import plan as plan_tools


class TraceStore:
    """Persist and render Agent execution traces."""

    def __init__(self, workspace_dir: str):
        self._root = Path(workspace_dir) / "traces"
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, trace: dict[str, Any]) -> str:
        """Save one trace and update this session's latest trace pointer."""
        session_id = trace.get("session_id") or "default"
        session_dir = self._root / self._safe_session_id(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        trace.setdefault("finished_at", self._now())
        filename = self._filename(trace)
        path = session_dir / filename
        data = json.dumps(trace, ensure_ascii=False, indent=2)
        path.write_text(data, encoding="utf-8")
        (session_dir / "last.json").write_text(data, encoding="utf-8")
        return str(path)

    def load_last(self, session_id: str) -> dict[str, Any] | None:
        """Load the latest trace for one session."""
        path = self._root / self._safe_session_id(session_id) / "last.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def format_last(self, session_id: str) -> str:
        """Return a Telegram-friendly text summary of the latest trace."""
        trace = self.load_last(session_id)
        if not trace:
            return "还没有可查看的 trace。先和 Agent 聊一轮，再发送 /trace。"
        return self.format_trace(trace)

    def format_trace(self, trace: dict[str, Any]) -> str:
        """Format a trace as compact plain text."""
        lines = [
            "最近一次 Agent Trace",
            f"- 会话: {trace.get('session_id', '-')}",
            f"- 开始: {trace.get('started_at', '-')}",
            f"- 结束: {trace.get('finished_at', '-')}",
            f"- 输入: {self._one_line(trace.get('user_input', ''), 300)}",
        ]

        if trace.get("error"):
            lines.append(f"- 错误: {self._one_line(trace['error'], 300)}")

        # 计划信息
        plan_summary = trace.get("plan_summary") or plan_tools.get_plan_summary()
        if plan_summary:
            lines.append(f"- 计划: {plan_summary}")

        for item in trace.get("iterations", []):
            lines.append("")
            lines.append(f"第 {item.get('index', '?')} 轮")
            lines.append(f"- LLM 返回: {item.get('result_type', '-')}")

            text_preview = item.get("text_preview")
            if text_preview:
                lines.append(f"- 文本片段: {self._one_line(text_preview, 300)}")

            for call in item.get("tool_calls", []):
                lines.append(f"- 工具: {call.get('name', '-')}")
                lines.append(f"  参数: {self._one_line(call.get('args', {}), 500)}")
                result = call.get("result_preview")
                if result:
                    lines.append(f"  结果: {self._one_line(result, 500)}")

        final_answer = trace.get("final_answer")
        if final_answer:
            lines.append("")
            lines.append(f"最终回复: {self._one_line(final_answer, 800)}")

        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3900] + "\n... trace 已截断，完整 JSON 在 workspace/traces 中。"
        return text

    @staticmethod
    def new_trace(msg) -> dict[str, Any]:
        return {
            "session_id": msg.session_id,
            "channel": msg.channel,
            "chat_id": msg.chat_id,
            "user_input": msg.text,
            "started_at": TraceStore._now(),
            "iterations": [],
            "final_answer": "",
            "error": None,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _filename(trace: dict[str, Any]) -> str:
        started = trace.get("started_at") or TraceStore._now()
        safe = started.replace(":", "").replace("-", "").replace(".", "_")
        return f"{safe}.json"

    @staticmethod
    def _safe_session_id(session_id: str) -> str:
        safe = []
        for ch in session_id:
            safe.append(ch if ch.isalnum() or ch in ("-", "_") else "_")
        return "".join(safe)[:120] or "default"

    @staticmethod
    def _one_line(value: Any, limit: int) -> str:
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        value = " ".join(value.split())
        if len(value) > limit:
            return value[:limit] + "..."
        return value
