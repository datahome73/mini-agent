"""
Plan/Execute 多步规划工具

提供 4 个工具让 Agent 对复杂任务先规划再执行：
- create_plan: 创建多步计划
- complete_step: 标记某步完成，自动激活下一步
- revise_plan: 中途插入新步骤
- get_plan: 查看当前计划进度

设计思路：
  现有 Agent 循环是「LLM 思考 → 批量执行工具 → 再思考」，适合单轮多步。
  但复杂任务（如查资料写报告、多步调研）需要显式的计划追踪，
  让 LLM 能分步推进、中途调整、并且知道自己做到哪一步了。
"""

from tools.base import Tool


class PlanManager:
    """管理多步计划的状态"""

    def __init__(self):
        self.steps: list[dict] = []
        self.goal: str = ""
        self._counter: int = 0

    def create_plan(self, goal: str, steps: list[str]) -> str:
        """创建计划，设置第一个步骤为进行中"""
        self.goal = goal
        self.steps = []
        self._counter = 0
        for desc in steps:
            self._counter += 1
            self.steps.append({
                "id": self._counter,
                "desc": desc,
                "status": "pending",
                "summary": "",
            })
        # 激活第一步
        if self.steps:
            self.steps[0]["status"] = "in_progress"
        return self._format()

    def complete_step(self, step_id: int, summary: str = "") -> str:
        """标记某步完成，自动激活下一个未完成的步骤"""
        found = False
        for i, s in enumerate(self.steps):
            if s["id"] == step_id:
                s["status"] = "done"
                s["summary"] = summary
                # 激活下一个未完成（pending）的步骤
                for j in range(i + 1, len(self.steps)):
                    if self.steps[j]["status"] == "pending":
                        self.steps[j]["status"] = "in_progress"
                        break
                found = True
                break
        if not found:
            return f"错误：未找到步骤 #{step_id}\n\n{self._format()}"
        return self._format()

    def revise_plan(self, after_step_id: int, new_steps: list[str]) -> str:
        """在指定步骤后插入新步骤（中途补充）"""
        insert_idx = len(self.steps)
        for i, s in enumerate(self.steps):
            if s["id"] == after_step_id:
                insert_idx = i + 1
                break

        new_entries = []
        for desc in new_steps:
            self._counter += 1
            new_entries.append({
                "id": self._counter,
                "desc": desc,
                "status": "pending",
                "summary": "",
            })

        self.steps[insert_idx:insert_idx] = new_entries
        return self._format()

    def fail_step(self, step_id: int, reason: str = "") -> str:
        """标记某步失败"""
        for s in self.steps:
            if s["id"] == step_id:
                s["status"] = "failed"
                s["summary"] = reason
                break
        return self._format()

    def get_plan(self) -> str:
        """查看当前计划状态"""
        return self._format()

    def has_active_plan(self) -> bool:
        """是否有未完成的计划"""
        if not self.steps:
            return False
        return any(s["status"] in ("pending", "in_progress") for s in self.steps)

    def _format(self) -> str:
        """格式化为人类可读的计划状态"""
        if not self.steps:
            return "📋 当前没有活跃计划。如需处理复杂任务，请先使用 create_plan 创建计划。"

        total = len(self.steps)
        done_count = sum(1 for s in self.steps if s["status"] == "done")

        lines = [
            f"📋 计划目标：{self.goal}",
            f"进度：{done_count}/{total} 步完成",
            "",
        ]
        for s in self.steps:
            icons = {
                "pending": "⏳",
                "in_progress": "▶️",
                "done": "✅",
                "failed": "❌",
            }
            icon = icons.get(s["status"], "⏳")
            summary = f" — {s['summary']}" if s["summary"] else ""
            lines.append(f"{icon} 步骤 #{s['id']}: {s['desc']}{summary}")

        return "\n".join(lines)

    def get_summary(self) -> str:
        """返回简短的计划摘要（给 trace 用）"""
        if not self.steps:
            return ""
        done = sum(1 for s in self.steps if s["status"] == "done")
        return f"{done}/{len(self.steps)} 步完成 — {self.goal[:80]}"


# ---- 单例 ----
_manager = PlanManager()


# ---- 工具实现 ----

async def _create_plan(goal: str, steps: list[str]) -> str:
    """创建多步执行计划"""
    return _manager.create_plan(goal, steps)


async def _complete_step(step_id: int, summary: str = "") -> str:
    """标记一个计划步骤已完成"""
    return _manager.complete_step(step_id, summary)


async def _revise_plan(after_step_id: int, new_steps: list[str]) -> str:
    """在指定步骤后插入新步骤"""
    return _manager.revise_plan(after_step_id, new_steps)


async def _get_plan() -> str:
    """查看当前计划状态"""
    return _manager.get_plan()


# ---- Tool 定义 ----

create_plan_tool = Tool(
    name="create_plan",
    description="为复杂/多步任务创建结构化执行计划。先列出步骤再逐步执行，每完成一步用 complete_step 标记。"
    "适用于：调研分析、多步代码修改、报告撰写等需要多个工具调用且前后有依赖关系的场景。",
    parameters={
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "任务目标，一句话描述要做什么",
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "按执行顺序排列的步骤描述列表。每个步骤应该是一个具体、可执行的动作。",
            },
        },
        "required": ["goal", "steps"],
    },
    fn=_create_plan,
)

complete_step_tool = Tool(
    name="complete_step",
    description="标记一个计划步骤已完成，并可选填写执行摘要。调用后自动激活下一步。",
    parameters={
        "type": "object",
        "properties": {
            "step_id": {
                "type": "integer",
                "description": "要标记为完成的步骤编号（创建计划时分配的数字 id）",
            },
            "summary": {
                "type": "string",
                "description": "执行结果摘要，例如找到了什么、做了什么修改（可选但推荐）",
            },
        },
        "required": ["step_id"],
    },
    fn=_complete_step,
)

revise_plan_tool = Tool(
    name="revise_plan",
    description="在指定步骤后插入新的执行步骤。当中途发现计划需要补充、遗漏了某步时使用。",
    parameters={
        "type": "object",
        "properties": {
            "after_step_id": {
                "type": "integer",
                "description": "在此步骤编号后插入新步骤",
            },
            "new_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要插入的新步骤描述列表",
            },
        },
        "required": ["after_step_id", "new_steps"],
    },
    fn=_revise_plan,
)

get_plan_tool = Tool(
    name="get_plan",
    description="查看当前活跃计划的执行进度和各步骤状态。",
    parameters={
        "type": "object",
        "properties": {},
    },
    fn=_get_plan,
)


def init_plan_tools():
    """重置 PlanManager 状态（在 Agent 启动时调用）"""
    _manager.steps = []
    _manager.goal = ""
    _manager._counter = 0


def get_plan_summary() -> str:
    """返回当前计划摘要（供 trace / 身份文本注入用）"""
    return _manager.get_summary()


def has_active_plan() -> bool:
    return _manager.has_active_plan()
