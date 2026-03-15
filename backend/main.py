from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os

from routes import router

# MongoDB配置
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB", "vlm_vla_tracker")

# 全局数据库实例
db = None


async def get_db():
    """依赖项：获取数据库实例"""
    if db is None:
        raise Exception("Database not connected. Please start MongoDB.")
    return db


# 修改路由以使用依赖注入
from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

# 导入路由函数
from routes import (
    get_papers, refresh_papers, get_projects, refresh_projects,
    get_news, get_all_data, refresh_all, get_stats
)

# 包装路由函数，注入db依赖
@api_router.get("/papers")
async def Papers(db=Depends(get_db)):
    return await get_papers(db)

@api_router.post("/papers/refresh")
async def Papers_refresh(db=Depends(get_db)):
    return await refresh_papers(db)

@api_router.get("/projects")
async def Projects(db=Depends(get_db)):
    return await get_projects(db)

@api_router.post("/projects/refresh")
async def Projects_refresh(db=Depends(get_db)):
    return await refresh_projects(db)

@api_router.get("/news")
async def News(db=Depends(get_db)):
    return await get_news(db)

@api_router.get("/all")
async def All(db=Depends(get_db)):
    return await get_all_data(db)

@api_router.post("/refresh-all")
async def All_refresh(db=Depends(get_db)):
    return await refresh_all(db)

@api_router.get("/stats")
async def Stats(db=Depends(get_db)):
    return await get_stats(db)


# 创建FastAPI应用
app = FastAPI(
    title="VLM/VLA Tracker",
    description="追踪最新视觉语言模型和视觉语言动作模型",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时连接MongoDB
@app.on_event("startup")
async def startup():
    global db
    try:
        client = AsyncIOMotorClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}")
        db = client[MONGO_DB]
        print(f"✅ Connected to MongoDB: {MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        db = None

# 关闭时断开连接
@app.on_event("shutdown")
async def shutdown():
    global db
    if db:
        db.client.close()
        print("✅ MongoDB connection closed")

# 挂载路由
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "message": "VLM/VLA Tracker API", 
        "docs": "/docs",
        "endpoints": [
            "/api/papers",
            "/api/projects", 
            "/api/news",
            "/api/all",
            "/api/stats",
            "/api/refresh-all"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)