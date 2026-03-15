import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import re
import logging
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Paper:
    """论文数据类"""

    def __init__(self, title: str, authors: str, abstract: str, url: str,
                 published_date: str = "", source: str = "arXiv", category: str = "Unknown"):
        self.title = title
        self.authors = authors
        self.abstract = abstract
        self.url = url
        self.published_date = published_date
        self.source = source
        self.category = category


class ArxivPaperFetcher:
    """修复版的arXiv论文获取器"""

    def __init__(self):
        # VLM关键词
        self.vlm_keywords = {
            'vision-language', 'visual language', 'multimodal', 'vlm',
            'vision transformer', 'vit', 'clip', 'blip', 'llava', 'flamingo',
            'cogvlm', 'qwen-vl', 'internvl', 'image captioning', 'vqa',
            'visual question answering', 'visual grounding', 'image understanding',
            '多模态', '视觉语言', '图像理解'
        }

        # VLA关键词
        self.vla_keywords = {
            'vision-language-action', 'vla', 'embodied', 'robot',
            'robotic', 'robotics', 'manipulation', 'rt-1', 'rt-2',
            'openvla', 'robot control', 'policy learning', 'grasping',
            '具身', '机器人', '机械臂'
        }

        # arXiv分类
        self.categories = ['cs.CV', 'cs.RO', 'cs.AI', 'cs.LG']

    async def fetch_papers(self, max_papers: int = 20, days_back: int = 30) -> List[Paper]:
        """获取论文的主方法"""
        all_papers = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for category in self.categories:
                try:
                    papers = await self._fetch_category_papers(client, category)
                    all_papers.extend(papers)
                    await asyncio.sleep(0.5)  # 礼貌性延迟
                except Exception as e:
                    logger.error(f"Error fetching {category}: {e}")

        # 过滤和评分
        relevant_papers = []
        for paper in all_papers:
            # 日期过滤
            if paper.published_date:
                try:
                    pub_date = datetime.strptime(paper.published_date, "%Y-%m-%d")
                    if pub_date < cutoff_date:
                        continue
                except:
                    pass

            # 计算相关性
            category = self._determine_category(paper)
            if category != "Unknown":
                paper.category = category
                relevant_papers.append(paper)

        logger.info(f"Found {len(relevant_papers)} relevant papers")
        return relevant_papers[:max_papers]

    async def _fetch_category_papers(self, client: httpx.AsyncClient, category: str) -> List[Paper]:
        """获取单个分类的论文 - 使用BeautifulSoup解析"""
        papers = []

        # 使用正确的API URL
        url = "https://export.arxiv.org/api/query"
        params = {
            'search_query': f'cat:{category}',
            'sortBy': 'submittedDate',
            'sortOrder': 'descending',
            'max_results': '50'  # 每个分类取50篇
        }

        try:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {category}: {response.status_code}")
                return []

            # 使用BeautifulSoup解析XML
            soup = BeautifulSoup(response.text, 'xml')

            # 查找所有entry
            entries = soup.find_all('entry')
            logger.info(f"Found {len(entries)} entries in {category}")

            for entry in entries:
                try:
                    # 提取标题
                    title_elem = entry.find('title')
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    title = re.sub(r'\s+', ' ', title)

                    # 提取作者
                    authors = []
                    for author in entry.find_all('author'):
                        name = author.find('name')
                        if name:
                            authors.append(name.text.strip())

                    # 提取摘要
                    summary_elem = entry.find('summary')
                    summary = summary_elem.text.strip() if summary_elem else ""
                    summary = re.sub(r'\s+', ' ', summary)

                    # 提取ID和链接
                    id_elem = entry.find('id')
                    if not id_elem:
                        continue

                    arxiv_id = id_elem.text.strip().split('/')[-1]
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                    # 提取发布日期
                    published_elem = entry.find('published')
                    published = published_elem.text[:10] if published_elem else ""

                    paper = Paper(
                        title=title,
                        authors=", ".join(authors[:10]),
                        abstract=summary[:1000],
                        url=pdf_url,
                        published_date=published,
                        source="arXiv",
                        category="Unknown"
                    )
                    papers.append(paper)

                except Exception as e:
                    logger.debug(f"Error parsing entry: {e}")
                    continue

            logger.info(f"Successfully parsed {len(papers)} papers from {category}")

        except Exception as e:
            logger.error(f"Error fetching {category}: {e}")

        return papers

    def _determine_category(self, paper: Paper) -> str:
        """判断论文类别"""
        text = f"{paper.title} {paper.abstract}".lower()

        # 检查是否包含VLA关键词
        has_vla = False
        for kw in self.vla_keywords:
            if kw.lower() in text:
                has_vla = True
                break

        # 检查是否包含VLM关键词
        has_vlm = False
        for kw in self.vlm_keywords:
            if kw.lower() in text:
                has_vlm = True
                break

        if has_vla and has_vlm:
            return "Both"
        elif has_vla:
            return "VLA"
        elif has_vlm:
            return "VLM"
        else:
            return "Unknown"


# 简化的调用函数
async def fetch_arxiv_papers(max_papers: int = 20, days_back: int = 30) -> List[Paper]:
    """
    从ArXiv获取最新VLM/VLA相关论文

    Args:
        max_papers: 最大返回论文数
        days_back: 考虑多少天内的论文

    Returns:
        论文列表
    """
    fetcher = ArxivPaperFetcher()

    try:
        papers = await fetcher.fetch_papers(
            max_papers=max_papers,
            days_back=days_back
        )

        # 打印结果
        if papers:
            print(f"\n找到 {len(papers)} 篇相关论文:")
            for i, p in enumerate(papers, 1):
                print(f"{i}. [{p.category}] {p.title[:80]}...")
                print(f"   作者: {p.authors[:50]}...")
                print(f"   日期: {p.published_date}")
                print()
        else:
            print("没有找到相关论文，尝试使用备用方法...")
            papers = await fetch_arxiv_papers_fallback(max_papers)

        return papers

    except Exception as e:
        logger.error(f"Error fetching arxiv papers: {e}")
        return []


async def fetch_arxiv_papers_fallback(max_papers: int = 20) -> List[Paper]:
    """备用方法：使用arXiv RSS源"""
    papers = []

    # arXiv RSS源
    rss_urls = [
        "https://export.arxiv.org/rss/cs.CV",
        "https://export.arxiv.org/rss/cs.RO",
        "https://export.arxiv.org/rss/cs.AI",
        "https://export.arxiv.org/rss/cs.LG",
    ]

    vlm_keywords = {'vision', 'visual', 'language', 'multimodal', 'image', 'vlm', 'clip', 'blip', 'llava'}
    vla_keywords = {'robot', 'action', 'manipulation', 'embodied', 'vla', 'rt-2', 'grasping'}

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for url in rss_urls:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'xml')

                    for item in soup.find_all('item')[:10]:
                        title = item.find('title').text.strip()
                        desc = item.find('description')
                        abstract = desc.text.strip() if desc else ""

                        text = (title + " " + abstract).lower()

                        # 判断类别
                        is_vlm = any(kw in text for kw in vlm_keywords)
                        is_vla = any(kw in text for kw in vla_keywords)

                        if is_vlm or is_vla:
                            category = "Both" if (is_vlm and is_vla) else ("VLA" if is_vla else "VLM")

                            papers.append(Paper(
                                title=title,
                                authors="",
                                abstract=abstract[:500],
                                url=item.find('link').text.strip(),
                                published_date="",
                                source="arXiv RSS",
                                category=category
                            ))
            except Exception as e:
                logger.error(f"Error fetching RSS {url}: {e}")

    return papers[:max_papers]


# 测试代码
async def test():
    print("测试 arXiv 论文获取功能...")
    papers = await fetch_arxiv_papers(max_papers=10, days_back=30)
    print(f"\n最终获取到 {len(papers)} 篇论文")


if __name__ == "__main__":
    asyncio.run(test())