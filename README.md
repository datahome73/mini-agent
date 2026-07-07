# 🐈 迷因迷你 Agent

一个极简的 AI Agent。System Prompt 从 provider 分离到独立的 identity.md 文件，与长期记忆一起由 AgentCore 组装。

## 特性

- **极简分层**：Channel → Bus → AgentCore → Provider + Tools，清晰可追踪
- **固定模型**：只支持 DeepSeek（API 兼容 OpenAI 格式）
- **两种模式**：CLI 交互模式 + Telegram Bot 模式
- **工具系统**：文件读写、Web 抓取/搜索、Shell 命令
- **记忆体系**：JSONL 会话历史 + Markdown 长期记忆
- **Docker 部署**：一键启动，数据持久化

## 目录结构

```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```
mini-agent/
├── main.py               # 入口
├── config.py             # 环境变量配置
├── bus.py                # 消息总线（消息定义）
├── agent_core.py         # ⭐ Agent 核心（Loop + Runner）
├── channels/
│   ├── base.py           # 渠道抽象
│   ├── cli.py            # 终端交互
│   └── telegram.py       # Telegram Bot
├── provider/
│   └── deepseek.py       # DeepSeek API 调用（纯管道，无业务逻辑）
├── tools/
│   ├── base.py           # 工具基类
│   ├── registry.py       # 工具注册表
│   ├── filesystem.py     # 文件工具
│   ├── web.py            # 网络工具
│   └── shell.py          # Shell 执行
├── memory/
│   ├── session.py        # 会话历史（JSONL）
│   ├── long_term.py      # 长期记忆（memory.md）
│   └── identity.md       # 角色身份（首次运行自动创建）
├── security/
│   └── workspace.py      # 路径沙箱
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```

## 配置

通过环境变量配置：

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 密钥 |
| `TELEGRAM_TOKEN` | ⚠️ Telegram 模式 | Telegram Bot Token |
| `DEEPSEEK_BASE_URL` | 可选 | API 地址（默认 `https://api.datahome73.com/v1`） |
| `DEEPSEEK_MODEL` | 可选 | 模型名（默认 `deepseek-v4-flash`） |
| `WORKSPACE_DIR` | 可选 | 数据目录（默认 `/app/data`） |
| `MAX_TOOL_ITERATIONS` | 可选 | 最大工具调用轮数（默认 10） |

## 运行

### CLI 模式

```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```bash
# 直接运行
export DEEPSEEK_API_KEY=sk-xxx
python main.py cli

# 或 Docker
docker build -t mini-agent .
docker run -it --rm \
  -e DEEPSEEK_API_KEY=sk-xxx \
  -v ./data:/app/data \
  mini-agent
```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```

### Telegram 模式

```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```bash
# 直接运行
export DEEPSEEK_API_KEY=sk-xxx
export TELEGRAM_TOKEN=xxx
python main.py telegram

# Docker Compose（推荐）
cp .env.example .env   # 填入你的密钥
docker compose up -d
```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```

## 插件系统

插件让你无需修改核心代码即可扩展 Agent 的能力。每个插件是一个  目录，导出  类。

### 插件结构



### 编写插件



### 使用插件

1. 在  下创建插件目录和 
2. 启动 agent，插件自动加载：
   

无需修改  或重启 Docker 以外的任何配置。

### 示例

项目自带  示例插件，提供  和  两个工具。可以直接删除或参考它编写自己的插件。

---

## 插件系统

插件让你无需修改核心代码即可扩展 Agent 的能力。每个插件是一个 `plugins/<name>/` 目录，导出 `Plugin` 类。

### 插件结构

```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```
plugins/
+-- example/               # 插件目录
|   +-- __init__.py        # 导出 Plugin 类
+-- your_plugin/
    +-- __init__.py
    +-- config.json         # 可选配置文件
    +-- helper.py           # 可选辅助模块
```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```

### 编写插件

```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```python
from tools.base import Tool


class Plugin:
    name = "my_plugin"                # 唯一标识
    description = "我的插件说明"

    def on_load(self, context: dict):
        """可选：初始化钩子（注册工具前调用）"""
        # context 包含：
        #   workspace_dir     - 工作空间路径
        #   agent_config      - Agent 配置字典
        #   long_term_memory  - 长期记忆对象（可选）
        pass

    def get_tools(self) -> list[Tool]:
        """返回本插件提供的工具列表"""
        return [my_tool]
```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```

### 使用插件

1. 在 `plugins/` 下创建插件目录和 `__init__.py`
2. 启动 agent，插件自动加载：
   ```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```
   2026-07-07 [INFO] plugin_loader: 插件已加载: example (2 个工具)
   ```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```

无需修改 `main.py` 或重启 Docker 以外的任何配置。

### 示例

项目自带 `plugins/example/` 示例插件，提供 `greet` 和 `count_tokens` 两个工具。可以直接删除或参考它编写自己的插件。

---

## 架构理解

```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```
你输入 (CLI / Telegram)
  │  InboundMessage
  ▼
bus.py → agent_core.py
            │
            ├─ memory/session.py    ← 加载最近对话
            ├─ memory/long_term.py  ← 加载长期记忆 + 角色身份
            ├─ provider/deepseek.py ← 调 DeepSeek（纯管道）
            ├─ tools/registry.py    ← 执行工具调用
            │     └─ 循环直到 LLM 产出最终回答
            ├─ memory/session.py    → 保存对话
            └─ 返回 OutboundMessage
  │
  ▼
发回给你
```
mini-agent/
+-- main.py               # 入口
+-- config.py             # 环境变量配置
+-- bus.py                # 消息总线（消息定义）
+-- agent_core.py         # Agent 核心（Loop + Runner）
+-- plugin_loader.py      # 插件加载器
+-- channels/
|   +-- base.py           # 渠道抽象
|   +-- cli.py            # 终端交互
|   +-- telegram.py       # Telegram Bot
+-- provider/
|   +-- deepseek.py       # DeepSeek API 调用
+-- tools/
|   +-- base.py           # 工具基类
|   +-- registry.py       # 工具注册表
|   +-- filesystem.py     # 文件工具
|   +-- http.py           # HTTP 请求
|   +-- web.py            # 网络工具
|   +-- shell.py          # Shell 执行
|   +-- memory_tool.py    # 记忆工具
+-- memory/
|   +-- session.py        # 会话历史（JSONL）
|   +-- long_term.py      # 长期记忆（memory.md）
|   +-- identity.md       # 角色身份
+-- plugins/
|   +-- example/          # 示例插件
|       +-- __init__.py
+-- security/
|   +-- workspace.py      # 路径沙箱
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
```

核心设计理念：**消息驱动、双循环（LLM ↔ Tool）、一次性写完、可追踪调试**。
