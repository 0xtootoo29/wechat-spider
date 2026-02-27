FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY app/ ./app/
COPY config/ ./config/

# 创建数据目录
RUN mkdir -p /app/data/articles /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
WORKDIR /app/app
CMD ["python", "main.py"]
