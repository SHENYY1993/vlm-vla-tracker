# 多阶段构建：后端服务
FROM python:3.10-slim as backend

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制后端依赖文件
COPY backend/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源代码
COPY backend/ ./backend/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "backend/main.py"]


# 多阶段构建：前端服务
FROM node:18-alpine as frontend

# 设置工作目录
WORKDIR /app

# 复制前端依赖文件
COPY frontend/package*.json ./

# 安装前端依赖（包括开发依赖用于构建）
RUN npm ci

# 复制前端源代码
COPY frontend/ ./

# 构建前端应用
RUN npm run build

# 生产环境：使用 Nginx 服务前端
FROM nginx:alpine

# 复制构建好的前端文件
COPY --from=frontend /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]