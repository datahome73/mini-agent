# 迷因迷你 Agent

一个用于学习 AI Agent 架构的极简项目。它从消息入口开始，经过 AgentCore 组装上下文，调用兼容 OpenAI 格式的模型接口，并在需要时执行工具，最后把结果发回给用户。

这个项目的目标不是做一个功能很重的助手，而是把 Agent 从 0 到 1 的关键模块拆清楚：消息渠道、模型调用、工具系统、短期记忆、长期记忆、插件扩展、运行轨迹。

## 特性

- **清晰分层**：Channel -> Bus -> AgentCore -> Provider + Tools
- **Telegram 优先**：日常使用通过 Telegram Bot 聊天
- **CLI 保留**：用于本地调试和后续扩展
- **人工审批流**：敏感操作（shell 命令、文件写入、POST/PUT/DELETE 请求）需用户确认才能执行，防止误操作
- **工具调用**：文件读写、Web 抓取/搜索、HTTP 请求、Shell 命令、记忆读写
- **上下文预算管理**：自动按 Token 预算分配系统提示、工具描述、会话历史的空间，超限自动截断旧消息
- **技能系统**：`skills/` 目录下的 .md 文档即技能，agent 用 `load_skill` / `list_skills` 自学，用 `learn_skill` 从网络下载新技能
- **多步规划**：复杂任务先 `create_plan` 列步骤，逐步推进，中途可 `revise_plan` 补充
- **凭证管理**：安全存储 API Key、Token，不污染长期记忆
- **MCP 工具**：通过标准 MCP 协议连接外部工具服务器，零代码扩展工具集
- **记忆体系**：JSONL 会话历史 + Markdown 长期记忆
- **插件系统**：在 `plugins/` 下新增插件即可扩展工具
- **Trace 调试**：通过 `/trace` 查看最近一次 Agent 执行轨迹
- **Docker 部署**：支持容器化运行和数据持久化

## 目录结构

```text
mini-agent/
|-- main.py               # 入口
|-- config.py             # 环境变量配置
|-- bus.py                # 消息定义
|-- agent_core.py         # Agent 核心循环
|-- plugin_loader.py      # 插件加载器
|-- channels/
|   |-- base.py           # 渠道抽象
|   |-- cli.py            # CLI 渠道
|   |-- telegram.py       # Telegram Bot 渠道
|-- provider/
|   |-- deepseek.py       # 模型接口封装
|-- tools/
|   |-- base.py           # 工具基类（含人工确认标记）
|   |-- registry.py       # 工具注册表
|   |-- confirm.py        # 人工审批流（Human-in-the-Loop）
|   |-- filesystem.py     # 文件工具
|   |-- http.py           # HTTP 请求工具
|   |-- web.py            # Web 抓取/搜索工具
|   |-- shell.py          # Shell 工具
|   |-- memory_tool.py    # 长期记忆工具
|   |-- skill.py          # 技能文档读取 + learn_skill
|   |-- credential_tool.py # 凭证管理工具
|   |-- plan.py           # 多步规划工具（Plan/Execute）
|-- skills/
|   |-- joke-teller.md    # 示例技能：讲笑话
|-- mcp_client/
|   |-- manager.py        # MCP 客户端管理器
|   |-- servers.json      # MCP Server 配置
|-- memory/
|   |-- session.py        # 短期会话历史
|   |-- long_term.py      # 长期记忆和角色身份
|   |-- context_manager.py # 上下文预算管理（Token 分配/截断）
|   |-- trace.py          # Agent 执行轨迹
|-- plugins/
|   |-- example/          # 示例插件
|-- security/
|   |-- workspace.py      # 工作目录路径沙箱
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
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
| `CONTEXT_MAX_TOKENS` | 否 | 上下文总预算，默认 `32768` |
| `CONTEXT_SYSTEM_MAX_TOKENS` | 否 | 系统提示+记忆预算，默认 `4096` |
| `CONTEXT_TOOLS_MAX_TOKENS` | 否 | 工具描述预算，默认 `4096` |
| `CONTEXT_HISTORY_MAX_TOKENS` | 否 | 会话历史预算，默认 `24576` |
| `CONTEXT_MIN_HISTORY` | 否 | 最少保留的历史消息数，默认 `2` |
| `CONTEXT_MAX_HISTORY` | 否 | 最多保留的历史消息数，默认 `100` |
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

## Trace 调试 + 上下文统计

### /trace — 执行轨迹

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

### /stats — 上下文使用报告

显示最近一次 Agent 处理的 Token 预算分配情况：

```text
📊 上下文使用报告
总计: 4520 / 32768 token (13%)
  ├ 身份+记忆: 680
  ├ 工具描述:  2100
  ├ 会话历史:  1200 (6 条消息)
  └ 当前输入:  540
```

在 Telegram 或 CLI 中输入 `/stats` 即可查看。如果上下文使用超过 90%，说明长对话中的旧消息可能会被自动截断。

## 上下文预算管理（Context Manager）

ContextManager 负责在每次 Agent 处理消息时，按 Token 预算分配各部分的上下文空间。它是 Agent 稳定运行长对话的关键——没有它，旧会话消息会无限膨胀消耗 Token。

### 预算结构

系统将上下文分为 4 个分区，各有独立预算：

| 分区 | 默认预算 | 内容 |
|------|----------|------|
| 身份+记忆 | 4096 token | 角色身份设定 + 长期记忆 |
| 工具描述 | 4096 token | 所有工具的 description 和参数 schema |
| 会话历史 | 24576 token | 最近 N 轮对话历史 |
| 当前输入 | 自动 | 当前用户消息 |

总预算默认 32768 token（可通过 `CONTEXT_MAX_TOKENS` 调整）。超预算时从**最旧的会话消息**开始丢弃，确保最近的对话始终保留。

### 查看预算使用

Telegram 或 CLI 中输入 `/stats` 查看当前分配情况。

## 架构理解
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

## 人工审批流（Human-in-the-Loop）

某些操作有潜在安全风险，Agent 不能擅自执行——需要先停住、问用户、等批准。

### 敏感工具

| 工具 | 触发条件 |
|------|---------|
| `run_command` | 任何命令 |
| `write_file` | 任何文件写入 |
| `http_request` | POST / PUT / DELETE / PATCH |

### 工作流程

```
用户: "帮我删除 /tmp/test.txt"
  ↓
Agent 检测到 run_command 是敏感工具
  ↓
⏸️ 挂起操作 → 返回确认提示
  ↓
用户: "是"
  ↓
▶️ 执行 run_command → 结果喂回 LLM → 生成最终回复
```

### 交互效果

当 Agent 调用敏感工具时，不直接执行，而是回复确认提示：

> ⚠️ **需要你确认这个操作：**
>
> 工具：`run_command`
> 参数：`cmd=rm /tmp/test.txt`
>
> 回复「**是**」确认执行，或「**否**」取消。

用户回复「是」后，Agent 执行该操作并继续完成后续逻辑。回复「否」则取消操作。

### 设计要点

- **会话级隔离**：不同聊天会话的挂起状态互不干扰
- **循环嵌套**：审批通过后如果 LLM 又调用了其他敏感工具，会再次触发确认
- **语义解析**：支持中英文确认/否定词（是/否/yes/no/确认执行/取消 等）
- **正常恢复**：确认操作后，消息上下文完整保留，LLM 自然延续之前的思路
- **双重路径**：非流式和流式（CLI / Telegram）都支持

### 扩展

如果需要自定义敏感规则，修改工具的 `requires_confirmation` 字段即可：

```python
# 整个工具标记为敏感
shell_tool = Tool(..., requires_confirmation=True)

# 按参数动态判断
http_request_tool = Tool(
    ...,
    requires_confirmation=lambda args: args.get("method", "GET") in ("POST", "PUT", "DELETE"),
)
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

## 技能系统（Skill）

技能系统让 Agent 能读取 `skills/` 下的 .md 文档来学习新能力——不再需要修改代码。

```python
list_skills()        # → 列出所有可用技能
load_skill("name")   # → 读取 skills/name.md 返回完整内容
```

Agent 在启动时被告知"遇到不熟悉的任务，先用 `list_skills` 看看有没有对应技能，再用 `load_skill` 学习"。每个 skill 是纯 Markdown，带 YAML frontmatter：

```markdown
---
name: joke-teller
description: "讲笑话 — 用户说'讲个笑话'时用"
---

# 讲笑话

当用户让你讲笑话时，从下面的列表中选一个回复。

1. 为什么程序员总是分不清万圣节和圣诞节？
   因为 Oct 31 == Dec 25。
...
```

### 从网络学习新技能

Agent 可以用 `learn_skill(url)` 从任意 URL 下载 .md 技能文档到 `skills/` 目录：

```
learn_skill("https://example.com/skills/meyo-registration.md", name="meyo-registration")
```

参数 `name` 可选，不传则自动从 URL 文件名或文档 frontmatter 推断。下载后立即可用 `load_skill` 加载。

## 凭证管理（Credential）

敏感信息（API Key、Token、密码）不适合放在长期记忆里。凭证管理系统把它们存为 `<WORKSPACE_DIR>/credentials.json`，独立于记忆文件。

### 工具

| 工具 | 功能 |
|------|------|
| `save_credential(name, value)` | 保存一条凭证（同名覆盖） |
| `get_credential(name)` | 读取凭证的值 |
| `list_credentials()` | 列出所有凭证名称（不显示值） |
| `delete_credential(name)` | 删除一条凭证 |

### 使用场景

```
你提供 API Key → agent 调用 save_credential 存到文件
需要调用外部 API → agent 调用 get_credential 读取密钥 → 用 http_request 调用
```

## 多步规划系统（Plan/Execute）

对于需要多步骤的复杂任务（如调研分析、多步代码修改、报告撰写），Agent 通过规划工具让执行过程可追踪、可调整。

### 工作流程

```
收到复杂请求
  → create_plan 列出步骤
  → 按顺序执行第 1 步 → complete_step #1
  → 执行第 2 步 → complete_step #2
  → （可选）revise_plan 发现遗漏，插入新步骤
  → 继续执行 → complete_step ...
  → 全部完成，总结回复用户
```

### 工具

| 工具 | 功能 |
|------|------|
| `create_plan(goal, steps)` | 创建多步计划，自动激活第一步 |
| `complete_step(step_id, summary)` | 标记某步完成，自动激活下一步 |
| `revise_plan(after_step_id, new_steps)` | 在指定步骤后插入新步骤 |
| `get_plan()` | 查看当前计划的完整进度 |

### 设计原则

- **简单任务跳过**：单步工具调用不需要规划，只在 3+ 步且有依赖关系时使用
- **进度自动推进**：`complete_step` 自动激活下一步，LLM 无需手动设置下一步
- **计划在上下文中**：每一步的完成状态通过工具调用结果返回对话，LLM 自然可见
- **Trace 可见**：`/trace` 中显示计划进度摘要
- **中途可调整**：`revise_plan` 让 LLM 能灵活应对执行途中的新发现

## MCP 工具系统

MCP（Model Context Protocol）是开放的 AI 工具协议。mini-agent 通过 `mcp_client/` 连接外部 MCP Server，把它们的工具注册到 `ToolRegistry` 中——**不改代码，加配置就行**。

### 配置方式

编辑 `mcp_client/servers.json`，添加想用的 MCP Server：

```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    },
    {
      "name": "github",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "xxx" }
    }
  ]
}
```

### 工作原理

```
启动时读取 servers.json
  → 每个 server 启动子进程（stdio）
  → MCP 协议握手，获取工具列表
  → 包装成 mcp_{server}_{tool} 格式
  → 注册到 ToolRegistry
  → Agent 直接用
```

### 效果

配置一个 filesystem server 就获得 14 个文件操作工具（read_file、write_file、search_files 等），配 GitHub server 就获得仓库/PR/Issue 全套工具。已有 1000+ 社区 MCP Server 可用。

## 数据文件

运行后，`WORKSPACE_DIR` 下会生成：

```text
memory.md              # 长期记忆
identity.md            # 角色身份
sessions/*.jsonl       # 会话历史
traces/*/last.json     # 最近一次执行轨迹
credentials.json       # 凭证存储（API Key、Token）
```

## 学习路线建议

1. 先读 `bus.py`，理解消息结构。
2. 再读 `agent_core.py`，理解 Agent 的 LLM <-> Tool 循环（特别是审批流的挂起/恢复逻辑）。
3. 然后读 `tools/`，理解工具如何暴露给模型（特别是 `tools/base.py` 的确认标记、`tools/confirm.py` 的审批管理器、`tools/skill.py` 的技能系统和 `tools/plan.py` 的规划系统）。
4. 接着读 `memory/`，理解短期记忆、长期记忆、`context_manager.py` 的 Token 预算管理、`trace.py` 的执行轨迹。
5. 最后读 `channels/telegram.py`，理解真实用户入口如何接入 Agent。
