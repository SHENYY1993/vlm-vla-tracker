# VLM/VLA Tracker

🤖 一个用于追踪最新视觉语言模型（VLM）和视觉语言动作模型（VLA）的 Web 应用

## 功能特性

- 📄 **论文追踪**：自动抓取 ArXiv 上最新的 VLM/VLA 相关论文
- 📁 **项目追踪**：收集 GitHub 和 HuggingFace 上热门的开源项目
- 📊 **数据统计**：实时统计 VLM/VLA 论文数量和项目热度
- 🔄 **自动更新**：支持手动刷新数据，保持信息最新
- 🎨 **现代化界面**：基于 Vue 3 + Element Plus 的响应式设计

## 技术栈

### 后端
- **FastAPI** - 高性能 Web 框架
- **MongoDB** - 数据存储
- **Motor** - MongoDB 异步驱动
- **BeautifulSoup** - HTML 解析
- **httpx** - HTTP 客户端

### 前端
- **Vue 3** - 前端框架
- **Element Plus** - UI 组件库
- **Vite** - 构建工具
- **Axios** - HTTP 客户端

## 项目结构

```
vlm-vla-tracker/
├── backend/              # FastAPI 后端服务
│   ├── main.py          # 应用入口
│   ├── models.py        # 数据模型定义
│   ├── routes.py        # API 路由
│   ├── scraper.py       # 数据抓取模块
│   └── requirements.txt # Python 依赖
├── frontend/            # Vue 3 前端应用
│   ├── src/
│   │   ├── App.vue      # 主应用组件
│   │   └── main.js      # 应用入口
│   ├── index.html       # HTML 模板
│   ├── package.json     # 前端依赖
│   └── vite.config.js   # Vite 配置
└── README.md            # 项目说明
```

## 快速开始

### 1. 环境准备

确保已安装以下软件：
- Python 3.8+
- Node.js 16+
- MongoDB

### 2. 后端设置

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动 MongoDB（如果未运行）
# Windows: mongod
# macOS/Linux: sudo systemctl start mongod

# 启动 FastAPI 服务
python main.py
```

**注意**：如果遇到 XML 解析错误，请确保安装了 lxml：
```bash
pip install lxml
```

服务将在 `http://localhost:8000` 启动，API 文档可在 `http://localhost:8000/docs` 查看。

### 3. 前端设置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:3000` 启动，并自动代理 API 请求到后端。

### 4. 访问应用

打开浏览器访问 `http://localhost:3000` 即可使用 VLM/VLA Tracker。

## API 接口

### 获取数据

- `GET /api/papers` - 获取所有论文
- `GET /api/projects` - 获取所有项目
- `GET /api/news` - 获取新闻（开发中）
- `GET /api/all` - 获取所有数据
- `GET /api/stats` - 获取统计信息

### 刷新数据

- `POST /api/papers/refresh` - 刷新论文数据
- `POST /api/projects/refresh` - 刷新项目数据
- `POST /api/refresh-all` - 一键刷新所有数据

## 数据来源

### 论文数据
- **ArXiv API**：自动抓取计算机视觉、自然语言处理、人工智能领域的最新论文
- **分类逻辑**：基于标题关键词自动分类为 VLM 或 VLA

### 项目数据
- **GitHub API**：搜索 vision language 相关的热门仓库
- **HuggingFace API**：获取多模态模型信息
- **去重机制**：避免重复项目

## 开发指南

### 添加新的数据源

1. 在 `backend/scraper.py` 中添加新的抓取函数
2. 在 `backend/routes.py` 中添加对应的 API 路由
3. 更新前端组件以显示新数据

### 自定义分类规则

修改 `scraper.py` 中的分类逻辑：

```python
# 论文分类示例
title_lower = paper_title.lower()
if any(kw in title_lower for kw in ['vla', 'robot', 'action', 'embodied', 'agent']):
    category = "VLA"
elif any(kw in title_lower for kw in ['vision', 'visual', 'multimodal', 'image']):
    category = "VLM"

# 项目分类示例
name_lower = project_name.lower()
if any(keyword in name_lower for keyword in ['vla', 'robot', 'action', 'embodied', 'agent']):
    category = "VLA"
```

## 部署

### Docker 部署

项目支持 Docker 部署，可自行编写 Dockerfile 和 docker-compose.yml。

### 生产环境

1. 使用 Gunicorn 运行 FastAPI
2. 配置 Nginx 反向代理
3. 设置 MongoDB 认证和备份
4. 配置前端构建和静态文件服务

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或联系开发者。