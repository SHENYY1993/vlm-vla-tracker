from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from bson import ObjectId
import json

from news_fetcher import fetch_news
from models import Paper, Project, News
from scraper import fetch_all_data, fetch_github_projects, fetch_huggingface_models
from news_fetcher import fetch_news as fetch_news_async
from paper_fetcher import fetch_arxiv_papers

router = APIRouter()

# 模拟数据库连接（实际使用MongoDB）
# 在main.py中会初始化


def serialize_doc(doc):
    """将MongoDB文档转换为JSON"""
    if doc is None:
        return None
    doc['_id'] = str(doc.get('_id', ''))
    return doc


# ==================== Papers ====================

@router.get("/papers")
async def get_papers(db):
    """获取所有论文"""
    papers = await db.papers.find().sort("created_at", -1).to_list(100)
    return [serialize_doc(p) for p in papers]


@router.post("/papers/refresh")
async def refresh_papers(db):
    """手动刷新论文数据"""
    # 清空旧数据
    await db.papers.delete_many({})
    
    # 获取新数据
    new_papers = await fetch_arxiv_papers()
    
    # 插入数据库
    if new_papers:
        papers_data = []
        for p in new_papers:
            papers_data.append({
                "title": p.title,
                "authors": p.authors,
                "abstract": p.abstract,
                "url": p.url,
                "published_date": p.published_date,
                "source": p.source,
                "category": p.category,
                "created_at": p.created_at
            })
        await db.papers.insert_many(papers_data)
    
    return {"message": f"刷新成功，获取 {len(new_papers)} 篇论文", "count": len(new_papers)}


# ==================== Projects ====================

@router.get("/projects")
async def get_projects(db):
    """获取所有项目"""
    projects = await db.projects.find().sort("stars", -1).to_list(100)
    return [serialize_doc(p) for p in projects]


@router.post("/projects/refresh")
async def refresh_projects(db):
    """手动刷新项目数据"""
    await db.projects.delete_many({})
    
    github_projects = await fetch_github_projects()
    hf_models = await fetch_huggingface_models()
    
    all_projects = github_projects + hf_models
    
    # 去重
    seen = set()
    unique_projects = []
    for p in all_projects:
        if p.name not in seen:
            seen.add(p.name)
            unique_projects.append(p)
    
    if unique_projects:
        projects_data = []
        for p in unique_projects:
            projects_data.append({
                "name": p.name,
                "description": p.description,
                "url": p.url,
                "stars": p.stars,
                "language": p.language,
                "owner": p.owner,
                "category": p.category,
                "updated_at": p.updated_at,
                "created_at": p.created_at
            })
        await db.projects.insert_many(projects_data)
    
    return {"message": f"刷新成功，获取 {len(unique_projects)} 个项目", "count": len(unique_projects)}


# ==================== News ====================

@router.get("/news")
async def get_news(db):
    """获取所有新闻"""
    news = await db.news.find().sort("created_at", -1).to_list(50)
    return [serialize_doc(n) for n in news]


@router.post("/news/refresh")
async def refresh_news(db):
    """手动刷新新闻数据"""
    await db.news.delete_many({})
    
    # 使用优化的新闻获取器
    news_items = await fetch_news_async(max_news=10)
    
    if news_items:
        # 将 News 对象转换为字典格式
        news_data = []
        for n in news_items:
            news_data.append({
                "title": n.title,
                "content": n.content,
                "url": n.url,
                "source": n.source,
                "published_date": n.published_date,
                "category": n.category,
                "relevance_score": n.relevance_score,
                "created_at": datetime.now()
            })
        await db.news.insert_many(news_data)
    
    return {"message": f"刷新成功，获取 {len(news_items)} 条新闻", "count": len(news_items)}


# ==================== All Data ====================

@router.get("/all")
async def get_all_data(db):
    """获取所有数据（论文、项目、新闻）"""
    papers = await db.papers.find().sort("created_at", -1).to_list(50)
    projects = await db.projects.find().sort("stars", -1).to_list(50)
    news = await db.news.find().sort("created_at", -1).to_list(20)
    
    return {
        "papers": [serialize_doc(p) for p in papers],
        "projects": [serialize_doc(p) for p in projects],
        "news": [serialize_doc(n) for n in news]
    }


@router.post("/refresh-all")
async def refresh_all(db):
    """一键刷新所有数据"""
    # 刷新论文
    await db.papers.delete_many({})
    papers = await fetch_arxiv_papers()
    if papers:
        papers_data = []
        for p in papers:
            papers_data.append({
                "title": p.title,
                "authors": p.authors,
                "abstract": p.abstract,
                "url": p.url,
                "published_date": p.published_date,
                "source": p.source,
                "category": p.category,
                "created_at": p.created_at
            })
        await db.papers.insert_many(papers_data)
    
    # 刷新项目
    await db.projects.delete_many({})
    github_projects = await fetch_github_projects()
    hf_models = await fetch_huggingface_models()
    all_projects = github_projects + hf_models
    
    seen = set()
    unique_projects = []
    for p in all_projects:
        if p.name not in seen:
            seen.add(p.name)
            unique_projects.append(p)
    
    if unique_projects:
        projects_data = []
        for p in unique_projects:
            projects_data.append({
                "name": p.name,
                "description": p.description,
                "url": p.url,
                "stars": p.stars,
                "language": p.language,
                "owner": p.owner,
                "category": p.category,
                "updated_at": p.updated_at,
                "created_at": p.created_at
            })
        await db.projects.insert_many(projects_data)
    
    return {
        "message": "刷新完成",
        "papers_count": len(papers),
        "projects_count": len(unique_projects)
    }


# ==================== Stats ====================

@router.get("/stats")
async def get_stats(db):
    """获取统计信息"""
    papers_count = await db.papers.count_documents({})
    projects_count = await db.projects.count_documents({})
    news_count = await db.news.count_documents({})
    
    vlm_count = await db.papers.count_documents({"category": "VLM"})
    vla_count = await db.papers.count_documents({"category": "VLA"})
    
    return {
        "total_papers": papers_count,
        "total_projects": projects_count,
        "total_news": news_count,
        "vlm_papers": vlm_count,
        "vla_papers": vla_count
    }