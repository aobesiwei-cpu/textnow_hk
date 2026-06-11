# TextNow 客服系统 - Docker 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8899

# 启动 Web 控制台
CMD ["python", "tn_web_dashboard.py"]
