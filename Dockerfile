# 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 拷贝依赖
COPY requirements.txt .

# 安装依赖（可加速：pip install -i https://pypi.tuna.tsinghua.edu.cn/simple）
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝项目代码
COPY . .

# 创建日志目录（避免权限问题）
RUN mkdir -p /app/logs

# 容器启动时运行
CMD ["python", "main.py"]
