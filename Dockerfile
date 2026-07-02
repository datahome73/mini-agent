FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 数据卷挂载点
VOLUME /app/data

# 默认启动 CLI 模式（可覆盖）
ENTRYPOINT ["python", "main.py"]
CMD ["cli"]
