FROM python:3.12-slim

WORKDIR /app

# 安装 Node.js（MCP Server 需要 npx 运行）
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 默认启动 Telegram 模式
ENTRYPOINT ["python", "main.py"]
CMD ["telegram"]
