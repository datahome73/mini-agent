"""
上下文窗口管理器 — 按 Token 预算智能分配上下文空间。

职责：
1. 估算每条消息的 token 数（基于字符数估算，无需额外依赖）
2. 按预算分配 system prompt、工具描述、会话历史的空间
3. 超预算时从最旧消息开始截断
4. 生成上下文使用报告（用于 /stats 命令）
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Token 估算参数
# 对于中英文混合文本（代码 + 中文对话），保守按 4 字符/token
_CHARS_PER_TOKEN = 4


@dataclass
class ContextConfig:
    """上下文窗口预算配置"""

    # 总预算上限（deepseek-v4-flash 支持 128K，保留安全余量）
    max_total_tokens: int = 32768

    # 各分区预算
    system_max_tokens: int = 4096       # 身份 + 长期记忆
    tools_max_tokens: int = 4096        # 工具描述文本
    history_max_tokens: int = 24576     # 会话历史

    # 历史消息硬约束
    min_history_messages: int = 2        # 最少保留的最近消息数
    max_history_messages: int = 100      # 绝对上限


@dataclass
class ContextReport:
    """上下文构建报告 — 供 /stats 和 trace 使用"""
    total_tokens: int = 0
    budget_total: int = 0
    system_tokens: int = 0
    tools_tokens: int = 0
    history_tokens: int = 0
    user_tokens: int = 0
    history_count: int = 0
    history_dropped: int = 0
    memory_truncated: bool = False
    tools_truncated: bool = False
    warnings: list = field(default_factory=list)


class ContextManager:
    """上下文窗口管理器"""

    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()
        self._last_report: Optional[ContextReport] = None

    @property
    def last_report(self) -> Optional[ContextReport]:
        return self._last_report

    # ---- 公开接口 ----

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """估算文本的 token 数（保守字符估算，无需 tokenizer 依赖）"""
        if not text:
            return 0
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def build_context(
        self,
        identity_text: str,
        memory_text: str,
        tools_desc: str,
        history: list[dict],
        user_text: str,
    ) -> tuple[list[dict], ContextReport]:
        """按预算构建上下文消息列表

        Args:
            identity_text: 角色身份文本
            memory_text: 长期记忆文本（可能为空）
            tools_desc: 工具描述文本（可能为空）
            history: 会话历史列表
            user_text: 当前用户输入

        Returns:
            (messages, report)
            messages: 截断后的消息列表 [system, history..., user]
            report: 预算使用报告
        """
        report = ContextReport()
        report.budget_total = self.config.max_total_tokens

        # ── 1. 构建 system prompt ──
        system_text = identity_text
        if memory_text:
            system_text += f"\n\n## 当前记忆\n{memory_text}"

        system_tokens = self.estimate_tokens(system_text)

        # 如果 system 超预算，截断记忆部分（保留 identity）
        if system_tokens > self.config.system_max_tokens:
            identity_tokens = self.estimate_tokens(identity_text)
            available = self.config.system_max_tokens - identity_tokens - 20  # 留余量
            if available > 50:
                memory_chars = available * _CHARS_PER_TOKEN
                memory_text = memory_text[:memory_chars] + "\n\n... (长期记忆已截断)"
            else:
                memory_text = ""

            system_text = identity_text
            if memory_text:
                system_text += f"\n\n## 当前记忆\n{memory_text}"

            report.memory_truncated = True
            report.warnings.append("长期记忆已截断")

        report.system_tokens = self.estimate_tokens(system_text)

        # ── 2. 工具描述 ──
        tools_text = ""
        if tools_desc:
            tools_text = f"\n\n## 可用工具\n{tools_desc}"

        tools_tokens = self.estimate_tokens(tools_text)
        if tools_tokens > self.config.tools_max_tokens:
            tools_chars = self.config.tools_max_tokens * _CHARS_PER_TOKEN
            tools_text = tools_text[:tools_chars]
            tools_text += "\n\n... (工具描述已截断)"
            report.tools_truncated = True
            report.warnings.append("工具描述已截断")

        report.tools_tokens = self.estimate_tokens(tools_text)

        # 组装完整 system prompt
        system_prompt = system_text + tools_text
        final_system = self.estimate_tokens(system_prompt)

        # ── 3. 用户输入 ──
        report.user_tokens = self.estimate_tokens(user_text)

        # ── 4. 计算历史预算 ──
        used_before_history = final_system + report.user_tokens + 20  # 安全余量
        history_budget = max(
            min(
                self.config.max_total_tokens - used_before_history,
                self.config.history_max_tokens,
            ),
            200,  # 至少保留 200 token 的历史空间
        )

        # ── 5. 截断历史 ──
        truncated_history, dropped = self._truncate_history(history, history_budget)
        report.history_dropped = dropped
        report.history_count = len(truncated_history)
        report.history_tokens = sum(
            self.estimate_tokens(m.get("content", "")) for m in truncated_history
        )

        # ── 6. 组装最终 messages ──
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(truncated_history)
        messages.append({"role": "user", "content": user_text})

        report.total_tokens = (
            report.system_tokens + report.tools_tokens
            + report.history_tokens + report.user_tokens
        )

        self._last_report = report
        return messages, report

    def format_report(self, report: Optional[ContextReport] = None) -> str:
        """格式化上下文报告为可读文本"""
        r = report or self._last_report
        if r is None:
            return "暂无上下文使用报告"

        pct = r.total_tokens * 100 // r.budget_total if r.budget_total > 0 else 0

        lines = [
            "📊 上下文使用报告",
            f"总计: {r.total_tokens} / {r.budget_total} token ({pct}%)",
            f"  ├ 身份+记忆: {r.system_tokens}",
            f"  ├ 工具描述:  {r.tools_tokens}",
            f"  ├ 会话历史:  {r.history_tokens} ({r.history_count} 条消息)",
            f"  └ 当前输入:  {r.user_tokens}",
        ]

        if r.history_dropped > 0:
            lines.append(f"\n丢弃了 {r.history_dropped} 条旧消息以节省空间")

        for w in r.warnings:
            lines.append(f"\n⚠️ {w}")

        if r.total_tokens > r.budget_total * 0.9:
            lines.append(f"\n⚠️ 上下文使用超过 90%，长对话可能被截断")

        return "\n".join(lines)

    # ---- 内部方法 ----

    def _truncate_history(self, history: list[dict], budget: int) -> tuple[list[dict], int]:
        """从最旧消息开始截断历史，直到预算内

        Returns:
            (truncated_history, dropped_count)
        """
        if not history:
            return [], 0

        dropped = 0

        # 先做副本，避免修改调用方的原始列表
        history = list(history)

        # 先按数量硬上限截断
        if len(history) > self.config.max_history_messages:
            dropped += len(history) - self.config.max_history_messages
            history = history[-self.config.max_history_messages:]

        # 计算当前总 token
        total = sum(self.estimate_tokens(m.get("content", "")) for m in history)

        # 在预算内，不动
        if total <= budget:
            return history, dropped

        # 从最旧开始丢弃，直到预算内或只剩最小数量
        while len(history) > self.config.min_history_messages:
            removed = history.pop(0)
            dropped += 1
            total -= self.estimate_tokens(removed.get("content", ""))
            if total <= budget:
                break

        if dropped > 0:
            logger.info(
                "上下文管理: 丢弃了 %d 条旧消息 (预算 %d, 剩余 %d 条)",
                dropped, budget, len(history),
            )

        return history, dropped
