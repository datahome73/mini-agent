"""
示例插件 — 演示 mini-agent 插件系统的标准写法。

本插件提供两个工具：
- `greet`：用指定风格打招呼
- `count_tokens`：估算文本 token 数（极简实现）
"""

from tools.base import Tool


async def greet(name: str = "世界", style: str = "normal") -> str:
    """用指定风格打招呼"""
    styles = {
        "normal": f"你好，{name}！",
        "fancy": f"✨ 尊敬的 {name}，您好！很高兴为您服务 ✨",
        "casual": f"嘿 {name}，咋样？",
        "robot": f"01001000 01100101 01101100 01101100 01101111 00101100 {name}",
    }
    greeting = styles.get(style, styles["normal"])
    return greeting


async def count_tokens(text: str) -> str:
    """估算文本的 token 数（简单按字符/4 估算）"""
    if not text:
        return "0"
    # 简单估算：中文约 1.5 字/token，英文约 4 字符/token
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    estimated = int(chinese_chars * 0.75 + other_chars * 0.25)
    if estimated < 1:
        estimated = 1
    return f"估算 token 数：{estimated}（{len(text)} 字符，其中 {chinese_chars} 个中文字符）"


# ===== 工具定义 =====
_greet_tool = Tool(
    name="greet",
    description="用指定风格向某人打招呼。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "打招呼的对象"},
            "style": {
                "type": "string",
                "enum": ["normal", "fancy", "casual", "robot"],
                "description": "打招呼的风格",
            },
        },
    },
    fn=greet,
)

_count_tokens_tool = Tool(
    name="count_tokens",
    description="估算一段文本的 token 数量，帮助用户判断上下文长度。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要估算的文本"},
        },
        "required": ["text"],
    },
    fn=count_tokens,
)


class Plugin:
    """示例插件 — 提供 greeting 和 token 估算工具"""

    name = "example"
    description = "示例插件：打招呼 + Token 估算工具"

    def __init__(self):
        self._workspace_dir = None

    def on_load(self, context: dict):
        """初始化时记录工作空间路径"""
        self._workspace_dir = context.get("workspace_dir", "/app/data")
        # 可以在这里做插件级别的初始化，比如读取自己的配置文件

    def get_tools(self) -> list[Tool]:
        return [_greet_tool, _count_tokens_tool]
