import httpx
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
from models import Paper, Project, News
from news_fetcher import fetch_news as fetch_news_async
import re

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
                
                # 生成中文翻译
                chinese_translation = _translate_abstract_to_chinese(summary[:500])
                
                papers.append(Paper(
                    title=title,
                    authors=authors,
                    abstract=summary[:500],
                    chinese_translation=chinese_translation,
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
                    
                    # 获取更详细的项目信息
                    detailed_info = await _fetch_github_repo_details(client, repo['full_name'])
                    
                    # 生成项目简介
                    description = _generate_github_project_description(repo, detailed_info)
                    
                    projects.append(Project(
                        name=repo['name'],
                        description=description,
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
                            
                            # 获取更详细的模型信息
                            detailed_info = await _fetch_hf_model_details(client, model['modelId'])
                            
                            # 生成模型简介
                            description = _generate_hf_model_description(model, detailed_info)
                            
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


# ==================== 辅助函数 ====================

async def _fetch_github_repo_details(client: httpx.AsyncClient, full_name: str) -> dict:
    """获取GitHub仓库的详细信息"""
    try:
        url = f"https://api.github.com/repos/{full_name}"
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching repo details for {full_name}: {e}")
    return {}


def _generate_github_project_description(repo: dict, detailed_info: dict) -> str:
    """生成GitHub项目的详细简介"""
    name = repo.get('name', '')
    description = repo.get('description', '')
    language = repo.get('language', '')
    stars = repo.get('stargazers_count', 0)
    
    # 从详细信息中获取更多数据
    topics = detailed_info.get('topics', [])
    forks = detailed_info.get('forks_count', 0)
    issues = detailed_info.get('open_issues_count', 0)
    
    # 生成简介
    parts = []
    
    # 基本描述
    if description:
        parts.append(description)
    
    # 技术栈
    if language:
        parts.append(f"使用 {language} 开发")
    
    # 统计信息
    stats = []
    if stars > 0:
        stats.append(f"stars: {stars}")
    if forks > 0:
        stats.append(f"forks: {forks}")
    if issues > 0:
        stats.append(f"issues: {issues}")
    
    if stats:
        parts.append(" | ".join(stats))
    
    # 主题标签
    if topics:
        topic_str = " ".join([f"#{topic}" for topic in topics[:5]])  # 只取前5个
        parts.append(f"标签: {topic_str}")
    
    # 项目类型判断
    name_lower = name.lower()
    if 'llava' in name_lower:
        parts.append("LLaVA系列模型，支持图像理解和问答")
    elif 'blip' in name_lower:
        parts.append("BLIP系列模型，专注于视觉语言理解")
    elif 'clip' in name_lower:
        parts.append("CLIP模型，实现图文匹配和理解")
    elif any(kw in name_lower for kw in ['robot', 'action', 'embodied', 'vla']):
        parts.append("视觉语言动作模型，支持机器人控制")
    
    return " | ".join(parts) if parts else "暂无详细描述"


async def _fetch_hf_model_details(client: httpx.AsyncClient, model_id: str) -> dict:
    """获取HuggingFace模型的详细信息"""
    try:
        url = f"https://huggingface.co/api/models/{model_id}"
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching model details for {model_id}: {e}")
    return {}


def _generate_hf_model_description(model: dict, detailed_info: dict) -> str:
    """生成HuggingFace模型的详细简介"""
    model_id = model.get('modelId', '')
    downloads = model.get('downloads', 0)
    
    # 从详细信息中获取更多数据
    card_data = detailed_info.get('card_data', {})
    pipeline_tag = model.get('pipeline_tag', '')
    tags = model.get('tags', [])
    
    # 生成简介
    parts = []
    
    # 基本信息
    if pipeline_tag:
        parts.append(f"任务类型: {pipeline_tag}")
    
    # 下载量
    if downloads > 0:
        parts.append(f"下载量: {downloads:,}")
    
    # 从card_data中获取描述
    if card_data.get('description'):
        desc = card_data['description'][:200]
        parts.append(f"描述: {desc}")
    elif card_data.get('summary'):
        summary = card_data['summary'][:200]
        parts.append(f"摘要: {summary}")
    
    # 标签
    if tags:
        relevant_tags = [tag for tag in tags if tag in ['vision', 'multimodal', 'language', 'image', 'text']]
        if relevant_tags:
            tag_str = ", ".join(relevant_tags[:3])
            parts.append(f"标签: {tag_str}")
    
    # 模型系列判断
    model_lower = model_id.lower()
    if 'llava' in model_lower:
        parts.append("LLaVA系列，支持图像问答和理解")
    elif 'blip' in model_lower:
        parts.append("BLIP系列，专注于视觉语言任务")
    elif 'clip' in model_lower:
        parts.append("CLIP模型，实现图文匹配")
    elif 'qwen' in model_lower and 'vl' in model_lower:
        parts.append("通义千问VL，多模态大模型")
    elif 'internvl' in model_lower:
        parts.append("InternVL，通用视觉语言模型")
    elif any(kw in model_lower for kw in ['robot', 'action', 'embodied', 'vla']):
        parts.append("视觉语言动作模型，支持机器人任务")
    
    return " | ".join(parts) if parts else "暂无详细描述"


# ==================== 中文翻译函数 ====================

def _translate_abstract_to_chinese(abstract: str) -> str:
    """将英文摘要翻译为中文"""
    if not abstract:
        return ""
    
    # 简单的关键词翻译映射
    translations = {
        # 常用术语
        'vision language model': '视觉语言模型',
        'multimodal': '多模态',
        'image understanding': '图像理解',
        'visual question answering': '视觉问答',
        'image captioning': '图像描述',
        'visual grounding': '视觉定位',
        'vision-language': '视觉-语言',
        'visual language': '视觉语言',
        
        # 模型名称
        'llava': 'LLaVA',
        'blip': 'BLIP',
        'clip': 'CLIP',
        'flamingo': 'Flamingo',
        
        # 任务类型
        'classification': '分类',
        'detection': '检测',
        'segmentation': '分割',
        'generation': '生成',
        'understanding': '理解',
        'reasoning': '推理',
        
        # 技术术语
        'transformer': '变换器',
        'attention': '注意力',
        'embedding': '嵌入',
        'pretraining': '预训练',
        'fine-tuning': '微调',
        'zero-shot': '零样本',
        'few-shot': '少样本',
        
        # 评价指标
        'accuracy': '准确率',
        'precision': '精确率',
        'recall': '召回率',
        'f1 score': 'F1分数',
        'bleu': 'BLEU分数',
        'rouge': 'ROUGE分数',
        
        # 其他常用词
        'state-of-the-art': '最先进的',
        'benchmark': '基准测试',
        'dataset': '数据集',
        'performance': '性能',
        'efficiency': '效率',
        'robustness': '鲁棒性',
        'generalization': '泛化能力'
    }
    
    # 转换为小写进行匹配
    abstract_lower = abstract.lower()
    translated = abstract
    
    # 替换翻译映射中的术语
    for english, chinese in translations.items():
        if english in abstract_lower:
            # 保持原始大小写，只替换内容
            pattern = re.escape(english)
            translated = re.sub(pattern, chinese, translated, flags=re.IGNORECASE)
    
    # 如果翻译后没有变化，返回原始摘要
    if translated == abstract:
        return abstract
    
    return translated


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
