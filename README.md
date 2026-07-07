# 迷因迷你 Agent

一个用于学习 AI Agent 架构的极简项目。它从消息入口开始，经过 AgentCore 组装上下文，调用兼容 OpenAI 格式的模型接口，并在需要时执行工具，最后把结果发回给用户。

这个项目的目标不是做一个功能很重的助手，而是把 Agent 从 0 到 1 的关键模块拆清楚：消息渠道、模型调用、工具系统、短期记忆、长期记忆、插件扩展、运行轨迹。

## 特性

- **清晰分层**：Channel -> Bus -> AgentCore -> Provider + Tools
- **Telegram 优先**：日常使用通过 Telegram Bot 聊天
- **CLI 保留**：用于本地调试和后续扩展
- **工具调用**：文件读写、Web 抓取/搜索、HTTP 请求、Shell 命令、记忆读写
- **记忆体系**：JSONL 会话历史 + Markdown 长期记忆
- **插件系统**：在 `plugins/` 下新增插件即可扩展工具
- **Trace 调试**：通过 `/trace` 查看最近一次 Agent 执行轨迹
- **Docker 部署**：支持容器化运行和数据持久化

## 目录结构

```text
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息定义
+-- agent_core.py         # Agent 核心循环
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # CLI 渠道
|   +-- telegram.py       # Telegram Bot 渠道
+-- provider/
|   +-- deepseek.py       # 模型接口封装
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求工具
|   +-- web.py            # Web 抓取/搜索工具
|   +-- shell.py          # Shell 工具
|   +-- memory_tool.py    # 长期记忆工具
+-- memory/
|   +-- session.py        # 短期会话历史
|   +-- long_term.py      # 长期记忆和角色身份
|   +-- trace.py          # Agent 执行轨迹
+-- plugins/
|   +-- example/          # 示例插件
+-- security/
|   +-- workspace.py      # 工作目录路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```

## 配置

通过环境变量配置：

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API 密钥 |
| `TELEGRAM_TOKEN` | Telegram 模式必填 | Telegram Bot Token |
| `DEEPSEEK_BASE_URL` | 否 | API 地址，默认 `https://api.datahome73.com/v1` |
| `DEEPSEEK_MODEL` | 否 | 模型名，默认 `deepseek-v4-flash` |
| `WORKSPACE_DIR` | 否 | 数据目录，默认 `/app/data` |
| `MAX_TOOL_ITERATIONS` | 否 | 最大工具调用轮数，默认 `10` |
| `SESSION_HISTORY_SIZE` | 否 | 每次带入的最近消息数，默认 `20` |
| `CRON_ENABLED` | 否 | 是否开启定时任务 |
| `CRON_INTERVAL` | 否 | 定时任务间隔，例如 `1d`、`2h`、`30m` |
| `CRON_PROMPT` | 否 | 定时任务发给 Agent 的提示词 |
| `CRON_CHAT_ID` | 否 | 定时任务要投递到的 Telegram chat id |

## 运行

### Telegram 模式

```bash
export DEEPSEEK_API_KEY=sk-xxx
export TELEGRAM_TOKEN=xxx
python main.py telegram
```

Docker Compose：

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 TELEGRAM_TOKEN
docker compose up -d
```

### CLI 模式

CLI 主要用于本地调试：

```bash
export DEEPSEEK_API_KEY=sk-xxx
python main.py cli
```

输入 `/quit` 退出。

## Trace 调试

Trace 用来观察 Agent 每一轮到底做了什么。它会记录：

- 用户输入
- LLM 每轮返回的是文本还是工具调用
- 工具名称和参数
- 工具返回结果摘要
- 最终回复
- 错误信息

在 Telegram 中发送：

```text
/trace
```

Bot 会返回当前 Telegram 会话最近一次 Agent 执行轨迹。CLI 中也可以输入 `/trace` 查看最近一次本地会话轨迹。

Trace 文件会写入工作目录：

```text
<WORKSPACE_DIR>/traces/<session_id>/last.json
<WORKSPACE_DIR>/traces/<session_id>/<timestamp>.json
```

`last.json` 始终指向这个会话最近一次运行，带时间戳的 JSON 用于长期排查和教学回放。

## 架构理解

```text
用户消息
  |
  v
Channel(telegram/cli)
  |
  v
InboundMessage
  |
  v
AgentCore
  |-- 加载短期会话历史
  |-- 加载长期记忆和身份设定
  |-- 组装 system/user messages
  |-- 调用 Provider
  |-- 如有 tool_calls，则执行工具并把结果放回上下文
  |-- 循环直到模型输出最终回答
  |-- 保存会话历史和 trace
  |
  v
OutboundMessage
  |
  v
Telegram / CLI 回复用户
```

## 工具系统

工具由 `tools.base.Tool` 定义，并注册到 `ToolRegistry`。每个工具都包含：

- `name`：工具名
- `description`：给模型看的能力说明
- `parameters`：JSON Schema 参数定义
- `fn`：实际执行函数

AgentCore 会把工具转换成 OpenAI function calling 格式传给模型。

## 插件系统

插件可以在不修改核心代码的情况下扩展 Agent 能力。每个插件是一个 `plugins/<name>/` 目录，并导出 `Plugin` 类。

```python
from tools.base import Tool


class Plugin:
    name = "my_plugin"
    description = "我的插件说明"

    def on_load(self, context: dict):
        pass

    def get_tools(self) -> list[Tool]:
        return [my_tool]
```

启动时，`PluginLoader` 会自动扫描 `plugins/`，加载插件并注册工具。

## 数据文件

运行后，`WORKSPACE_DIR` 下会生成：

```text
memory.md              # 长期记忆
identity.md            # 角色身份
sessions/*.jsonl       # 会话历史
traces/*/last.json     # 最近一次执行轨迹
```

## 学习路线建议

1. 先读 `bus.py`，理解消息结构。
2. 再读 `agent_core.py`，理解 Agent 的 LLM <-> Tool 循环。
3. 然后读 `tools/`，理解工具如何暴露给模型。
4. 接着读 `memory/`，理解短期记忆、长期记忆和 trace。
5. 最后读 `channels/telegram.py`，理解真实用户入口如何接入 Agent。
