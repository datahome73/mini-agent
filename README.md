# 🐈 南欧迷你 Agent

一个极简的 AI Agent，基于 **nanobot** 的架构思路重新实现，用于学习和研究。

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
├── main.py               # 入口
├── config.py             # 环境变量配置
├── bus.py                # 消息总线（消息定义）
├── agent_core.py         # ⭐ Agent 核心（Loop + Runner）
├── channels/
│   ├── base.py           # 渠道抽象
│   ├── cli.py            # 终端交互
│   └── telegram.py       # Telegram Bot
├── provider/
│   └── deepseek.py       # DeepSeek API 封装
├── tools/
│   ├── base.py           # 工具基类
│   ├── registry.py       # 工具注册表
│   ├── filesystem.py     # 文件工具
│   ├── web.py            # 网络工具
│   └── shell.py          # Shell 执行
├── memory/
│   ├── session.py        # 会话历史（JSONL）
│   └── long_term.py      # 长期记忆（Markdown）
├── security/
│   └── workspace.py      # 路径沙箱
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 配置

通过环境变量配置：

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 密钥 |
| `TELEGRAM_TOKEN` | ⚠️ Telegram 模式 | Telegram Bot Token |
| `DEEPSEEK_BASE_URL` | 可选 | API 地址（默认 `https://api.deepseek.com`） |
| `DEEPSEEK_MODEL` | 可选 | 模型名（默认 `deepseek-chat`） |
| `WORKSPACE_DIR` | 可选 | 数据目录（默认 `/app/data`） |
| `MAX_TOOL_ITERATIONS` | 可选 | 最大工具调用轮数（默认 10） |

## 运行

### CLI 模式

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

### Telegram 模式

```bash
# 直接运行
export DEEPSEEK_API_KEY=sk-xxx
export TELEGRAM_TOKEN=xxx
python main.py telegram

# Docker Compose（推荐）
cp .env.example .env   # 填入你的密钥
docker compose up -d
```

## 架构理解

```
你输入 (CLI / Telegram)
  │  InboundMessage
  ▼
bus.py → agent_core.py
            │
            ├─ memory/session.py    ← 加载最近对话
            ├─ memory/long_term.py  ← 加载长期记忆
            ├─ provider/deepseek.py ← 调 DeepSeek
            ├─ tools/registry.py    ← 执行工具调用
            │     └─ 循环直到 LLM 产出最终回答
            ├─ memory/session.py    → 保存对话
            └─ 返回 OutboundMessage
  │
  ▼
发回给你
```

核心设计理念：**消息驱动、双循环（LLM ↔ Tool）、一次性写完、可追踪调试**。
