from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Paper(BaseModel):
    id: Optional[str] = None
    title: str
    authors: str
    abstract: str
    chinese_translation: Optional[str] = None  # 中文翻译
    url: str
    published_date: Optional[str] = None
    source: str  # arxiv, huggingface, github
    category: str  # VLM, VLA, Both
    created_at: datetime = datetime.now()


class Project(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    url: str
    stars: Optional[int] = 0
    language: Optional[str] = None
    owner: str
    category: str  # VLM, VLA
    updated_at: Optional[str] = None
    created_at: datetime = datetime.now()


class News(BaseModel):
    id: Optional[str] = None
    title: str
    content: str
    url: str
    source: str
    published_date: Optional[str] = None
    category: str  # VLM, VLA, General
    created_at: datetime = datetime.now()