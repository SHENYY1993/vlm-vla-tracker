import httpx
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
from models import Paper, Project, News
from news_fetcher import fetch_news as fetch_news_async

# ArXiv API (no key needed)
ARXIV_VLM_URL = "https://export.arxiv.org/api/query?search_query=cat:cs.CV+OR+cat:cs.CL+OR+cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=30"

# HuggingFace trending (需要模拟浏览器)
HF_TRENDING_URL = "https://huggingface.co/models?sort=downloads&search=vision+language"

# GitHub trending
GITHUB_VLM_SEARCH = "https://api.github.com/search/repositories?q=vision+language+model+language:python&sort=stars&order=desc"


async def fetch_arxiv_papers() -> List[Paper]:
    """从ArXiv获取最新VLM/VLA相关论文"""
    papers = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(ARXIV_VLM_URL)
            soup = BeautifulSoup(response.text, 'xml')
            
            for entry in soup.find_all('entry')[:20]:
                title = entry.find('title').text.strip()
                authors = ", ".join([a.text for a in entry.find_all('author')])
                summary = entry.find('summary').text.strip()
                url = entry.find('id').text
                published = entry.find('published').text[:10]
                
                # 判断类别
                category = "VLM"
                title_lower = title.lower()
                if any(kw in title_lower for kw in ['vla', 'robot', 'action', 'embodied', 'agent']):
                    category = "VLA"
                elif any(kw in title_lower for kw in ['vision', 'visual', 'multimodal', 'image']):
                    category = "VLM"
                
                papers.append(Paper(
                    title=title,
                    authors=authors,
                    abstract=summary[:500],
                    url=url,
                    published_date=published,
                    source="arXiv",
                    category=category
                ))
    except Exception as e:
        print(f"Error fetching arxiv: {e}")
    return papers


async def fetch_github_projects() -> List[Project]:
    """从GitHub获取热门VLM/VLA项目"""
    projects = []
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(GITHUB_VLM_SEARCH, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for repo in data.get('items', [])[:15]:
                    category = "VLM"
                    name_lower = repo['name'].lower()
                    if any(kw in name_lower for kw in ['vla', 'robot', 'action', 'embodied', 'agent']):
                        category = "VLA"
                    
                    projects.append(Project(
                        name=repo['name'],
                        description=repo['description'] or "",
                        url=repo['html_url'],
                        stars=repo['stargazers_count'],
                        language=repo['language'],
                        owner=repo['owner']['login'],
                        category=category,
                        updated_at=repo.get('updated_at', '')[:10]
                    ))
    except Exception as e:
        print(f"Error fetching github: {e}")
    return projects


async def fetch_huggingface_models() -> List[Project]:
    """从HuggingFace获取热门多模态模型"""
    projects = []
    try:
        # 使用HF公开API
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 搜索视觉语言模型
            search_queries = ["vision language", "multimodal", "LLaVA", "BLIP"]
            
            for query in search_queries:
                url = f"https://huggingface.co/api/models?search={query}&sort=downloads&direction=-1&limit=5"
                response = await client.get(url)
                if response.status_code == 200:
                    models = response.json()
                    for model in models:
                        if model.get('modelId'):
                            # 简单判断类别
                            model_id = model['modelId'].lower()
                            category = "VLM"
                            if any(kw in model_id for kw in ['vla', 'robot', 'embodied']):
                                category = "VLA"
                            
                            # 获取更详细的描述信息
                            description = ""
                            if model.get('card_data'):
                                card_data = model['card_data']
                                # 优先使用 modelCardData 中的 description
                                if card_data.get('description'):
                                    description = card_data['description']
                                # 其次使用 summary
                                elif card_data.get('summary'):
                                    description = card_data['summary']
                                # 最后使用 modelCardData 中的其他字段
                                elif card_data.get('modelCardData', {}).get('description'):
                                    description = card_data['modelCardData']['description']
                                # 尝试获取其他可能的描述字段
                                elif card_data.get('modelCardData', {}).get('model_details', {}).get('description'):
                                    description = card_data['modelCardData']['model_details']['description']
                                elif card_data.get('modelCardData', {}).get('model_details', {}).get('model_description'):
                                    description = card_data['modelCardData']['model_details']['model_description']
                            
                            # 如果没有详细描述，使用 pipeline_tag 作为备选
                            if not description and model.get('pipeline_tag'):
                                description = model['pipeline_tag']
                            
                            projects.append(Project(
                                name=model['modelId'],
                                description=description,
                                url=f"https://huggingface.co/{model['modelId']}",
                                stars=model.get('downloads', 0),
                                language=None,
                                owner=model['modelId'].split('/')[0] if '/' in model['modelId'] else model['modelId'],
                                category=category,
                                updated_at=None
                            ))
    except Exception as e:
        print(f"Error fetching huggingface: {e}")
    return projects[:15]


async def fetch_news() -> List[News]:
    """获取VLM/VLA相关新闻 - 使用优化的news_fetcher"""
    try:
        # 使用优化的新闻获取器
        news_items = await fetch_news_async(max_news=10)
        return news_items
    except Exception as e:
        print(f"Error using news_fetcher: {e}")
        
        # 备用方案：返回示例新闻
        example_news = [
            News(
                title="OpenAI 发布新一代多模态模型",
                content="OpenAI 宣布推出支持视觉理解的新一代模型，能够处理图像和文本输入。",
                url="https://openai.com/blog/new-model",
                source="OpenAI Blog",
                published_date="2024-01-15",
                category="VLM"
            ),
            News(
                title="Google DeepMind 展示机器人视觉动作系统",
                content="DeepMind 研究团队开发出能够通过视觉理解执行复杂动作的机器人系统。",
                url="https://deepmind.com/blog/robot-vision",
                source="DeepMind Blog",
                published_date="2024-01-10",
                category="VLA"
            )
        ]
        return example_news


# 手动更新所有数据
async def fetch_all_data():
    """获取所有数据"""
    papers = await fetch_arxiv_papers()
    github_projects = await fetch_github_projects()
    hf_models = await fetch_huggingface_models()
    
    # 合并项目（去重）
    all_projects = github_projects + hf_models
    seen = set()
    unique_projects = []
    for p in all_projects:
        if p.name not in seen:
            seen.add(p.name)
            unique_projects.append(p)
    
    news = await fetch_news()
    
    return {
        "papers": papers,
        "projects": unique_projects,
        "news": news,
        "timestamp": datetime.now().isoformat()
    }