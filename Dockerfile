FROM python:3.10-slim

WORKDIR /app

# 复制项目文件
COPY README.md pyproject.toml ./
COPY src/ ./src/

# 安装依赖
RUN pip install --no-cache-dir -e .

# 暴露 MCP 服务器使用的任何端口
# EXPOSE 8080

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 运行服务器
ENTRYPOINT ["python", "-m", "mcp_server_sls"] 