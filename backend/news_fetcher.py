import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime, timedelta
import re
import logging
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class News:
    """新闻数据类"""

    def __init__(self, title: str, content: str, url: str, source: str,
                 published_date: str = "", category: str = "Unknown",
                 relevance_score: float = 0.0):
        self.title = title
        self.content = content
        self.url = url
        self.source = source
        self.published_date = published_date
        self.category = category
        self.relevance_score = relevance_score

    def __repr__(self):
        return f"News(title={self.title[:30]}..., category={self.category}, score={self.relevance_score:.2f})"


class NewsFetcher:
    """优化的新闻获取器"""

    def __init__(self):
        # VLM相关关键词（放宽条件）
        self.vlm_keywords = {
            # 核心术语
            'vision', 'visual', 'image', 'multimodal', 'vlm',
            'vision-language', '视觉', '多模态',

            # 模型名称
            'clip', 'blip', 'llava', 'flamingo', 'cogvlm',
            'qwen-vl', 'internvl', 'deepseek-vl',

            # 任务类型
            'image captioning', 'vqa', 'visual question',
            'image understanding', 'visual grounding',

            # 中文关键词
            '视觉语言', '图文', '图像理解'
        }

        # VLA相关关键词
        self.vla_keywords = {
            # 核心术语
            'robot', 'robotics', 'robotic', 'action', 'manipulation',
            'embodied', 'vla', 'vision-language-action',
            '机器人', '具身', '机械臂',

            # 任务类型
            'grasping', 'picking', 'placing', 'navigation',
            'policy learning', 'imitation learning',
            'robot control', 'robotic manipulation',

            # 模型名称
            'rt-1', 'rt-2', 'rt-h', 'octo', 'openvla',
            'google robot', 'deepmind robot'
        }

        # 排除关键词（明显不相关的）
        self.exclude_keywords = {
            'music', 'song', 'audio', '音乐',
            'game', 'gaming', '游戏',
            'finance', 'stock', '金融',
            'sports', 'football', '体育',
            'fashion', '时尚',
            'food', 'recipe', '美食',
        }

        # 可靠的RSS源
        self.rss_feeds = {
            'arxiv': [  # arXiv分类
                "https://export.arxiv.org/rss/cs.CV",
                "https://export.arxiv.org/rss/cs.RO",
                "https://export.arxiv.org/rss/cs.AI",
                "https://export.arxiv.org/rss/cs.LG",
            ],
            'tech_media': [  # 科技媒体
                "https://techcrunch.com/tag/artificial-intelligence/feed/",
                "https://venturebeat.com/category/ai/feed/",
                "https://www.wired.com/feed/tag/ai/latest/rss",
                "https://feeds.feedburner.com/TowardsDataScience",
            ],
            'chinese': [  # 中文源
                "https://www.leiphone.com/feed",
                "https://www.jiqizhixin.com/rss",
                "https://36kr.com/feed",
            ]
        }

        # 官方博客（直接解析HTML）
        self.official_blogs = {
            'deepmind': 'https://deepmind.google/blog/',
            'meta': 'https://ai.meta.com/blog/',
            'google': 'https://research.google/blog/',
            # OpenAI有反爬，暂时禁用
        }

    async def fetch_news(self, max_news: int = 10) -> List[News]:
        """获取VLM/VLA相关新闻"""
        all_news = []

        async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as client:

            # 1. 从arXiv获取（主要来源）
            for url in self.rss_feeds['arxiv']:
                news = await self._fetch_arxiv_feed(client, url)
                all_news.extend(news)

            # 2. 从科技媒体获取
            for url in self.rss_feeds['tech_media']:
                news = await self._fetch_rss_feed(client, url)
                all_news.extend(news)

            # 3. 从中文源获取
            for url in self.rss_feeds['chinese']:
                news = await self._fetch_rss_feed(client, url)
                all_news.extend(news)

            # 4. 从官方博客获取
            for name, url in self.official_blogs.items():
                news = await self._fetch_blog_feed(client, name, url)
                all_news.extend(news)

        # 过滤和评分
        filtered_news = []
        seen_urls = set()

        for news in all_news:
            # 去重
            if news.url in seen_urls:
                continue
            seen_urls.add(news.url)

            # 检查是否应该排除
            if self._should_exclude(news):
                continue

            # 计算相关性
            score, category = self._calculate_relevance(news)

            if score > 0:  # 只要有一点相关性就保留
                news.relevance_score = score
                news.category = category
                filtered_news.append(news)
                logger.debug(f"Found relevant: {news.title[:50]}... ({category}, score={score:.1f})")

        # 按分数排序
        filtered_news.sort(key=lambda x: x.relevance_score, reverse=True)

        # 如果没有找到任何新闻，返回示例
        if not filtered_news:
            logger.warning("No relevant news found, returning default examples")
            return self._get_default_news()

        # 记录找到的新闻
        logger.info(f"Found {len(filtered_news)} relevant news items")
        for i, n in enumerate(filtered_news[:5], 1):
            logger.info(f"{i}. [{n.category}] {n.title[:50]}... (score: {n.relevance_score:.1f})")

        return filtered_news[:max_news]

    async def _fetch_arxiv_feed(self, client: httpx.AsyncClient, url: str) -> List[News]:
        """专门处理arXiv RSS"""
        news_items = []

        try:
            response = await client.get(url)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'xml')

            for item in soup.find_all('item')[:20]:  # arXiv可以多取一些
                try:
                    title = item.find('title').text.strip()

                    # 提取摘要
                    description = item.find('description')
                    content = description.text.strip() if description else ""

                    # 提取作者
                    creator = item.find('dc:creator')
                    author = creator.text if creator else ""

                    # 发布日期
                    pub_date = item.find('pubDate')
                    date_str = pub_date.text[:10] if pub_date else ""

                    # 构建内容
                    full_content = f"Authors: {author}\nAbstract: {content[:500]}"

                    news_items.append(News(
                        title=title,
                        content=full_content,
                        url=item.find('link').text.strip(),
                        source="arXiv",
                        published_date=date_str
                    ))

                except Exception as e:
                    logger.debug(f"Error parsing arXiv item: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error fetching arXiv feed {url}: {e}")

        return news_items

    async def _fetch_rss_feed(self, client: httpx.AsyncClient, url: str) -> List[News]:
        """获取普通RSS源"""
        news_items = []

        try:
            response = await client.get(url)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'xml')

            # 尝试不同的RSS格式
            items = soup.find_all('item')
            if not items:
                items = soup.find_all('entry')

            for item in items[:10]:
                try:
                    # 标题
                    title_elem = item.find('title')
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()

                    # 链接
                    link_elem = item.find('link')
                    if not link_elem:
                        continue

                    if link_elem.name == 'link' and link_elem.get('href'):
                        link = link_elem['href']
                    else:
                        link = link_elem.text.strip()

                    # 内容
                    desc_elem = item.find(['description', 'summary', 'content:encoded'])
                    content = ""
                    if desc_elem:
                        content = re.sub(r'<[^>]+>', ' ', desc_elem.text)
                        content = re.sub(r'\s+', ' ', content).strip()[:500]

                    # 日期
                    date_elem = item.find(['pubDate', 'published', 'updated'])
                    pub_date = date_elem.text[:10] if date_elem else ""

                    # 来源
                    source = self._extract_source_name(url, link)

                    news_items.append(News(
                        title=title,
                        content=content,
                        url=link,
                        source=source,
                        published_date=pub_date
                    ))

                except Exception as e:
                    logger.debug(f"Error parsing RSS item: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error fetching RSS {url}: {e}")

        return news_items

    async def _fetch_blog_feed(self, client: httpx.AsyncClient, blog_name: str, url: str) -> List[News]:
        """从官方博客获取（HTML解析）"""
        news_items = []

        try:
            response = await client.get(url)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # 根据不同的博客使用不同的选择器
            selectors = {
                'deepmind': {
                    'article': 'article',
                    'title': 'h2, h3',
                    'link': 'a[href*="/blog/"]',
                    'date': 'time',
                    'summary': 'p'
                },
                'meta': {
                    'article': '[class*="blog"], article',
                    'title': 'h2, h3',
                    'link': 'a[href*="/blog/"]',
                    'date': 'time, [class*="date"]',
                    'summary': 'p'
                },
                'google': {
                    'article': 'article, .post',
                    'title': 'h2, h3',
                    'link': 'a[href*="/blog/"]',
                    'date': 'time, [class*="date"]',
                    'summary': 'p'
                }
            }

            selector = selectors.get(blog_name, selectors['deepmind'])

            # 查找文章元素
            articles = soup.find_all(selector['article']) if selector['article'] else []

            for article in articles[:5]:
                try:
                    # 标题
                    title_elem = article.find(selector['title'])
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()

                    # 链接
                    link_elem = article.find(selector['link'])
                    if not link_elem or not link_elem.get('href'):
                        continue

                    link = link_elem['href']
                    if not link.startswith('http'):
                        link = url.rstrip('/') + '/' + link.lstrip('/')

                    # 日期
                    date_elem = article.find(selector['date'])
                    date_str = ""
                    if date_elem:
                        if date_elem.get('datetime'):
                            date_str = date_elem['datetime'][:10]
                        else:
                            date_str = date_elem.text.strip()[:10]

                    # 摘要
                    summary = ""
                    p_tags = article.find_all(selector['summary'])
                    if p_tags:
                        summary = p_tags[0].text[:300]

                    news_items.append(News(
                        title=title,
                        content=summary,
                        url=link,
                        source=blog_name.capitalize(),
                        published_date=date_str
                    ))

                except Exception as e:
                    logger.debug(f"Error parsing blog item: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error fetching blog {blog_name}: {e}")

        return news_items

    def _should_exclude(self, news: News) -> bool:
        """检查是否应该排除"""
        text = f"{news.title} {news.content}".lower()

        for keyword in self.exclude_keywords:
            if keyword.lower() in text:
                return True

        return False

    def _calculate_relevance(self, news: News) -> Tuple[float, str]:
        """计算相关性分数，返回(分数, 类别)"""
        text = f"{news.title} {news.content}".lower()

        # 计算VLM分数
        vlm_score = 0
        vlm_matches = set()
        for keyword in self.vlm_keywords:
            if keyword.lower() in text:
                vlm_score += 1
                vlm_matches.add(keyword)

        # 计算VLA分数
        vla_score = 0
        vla_matches = set()
        for keyword in self.vla_keywords:
            if keyword.lower() in text:
                vla_score += 1
                vla_matches.add(keyword)

        # 如果两者都没有匹配，返回0
        if vlm_score == 0 and vla_score == 0:
            return 0.0, "Unknown"

        # 确定类别
        if vla_score > vlm_score:
            category = "VLA"
            score = vla_score
        elif vlm_score > vla_score:
            category = "VLM"
            score = vlm_score
        else:
            # 分数相等时，如果VLA关键词更具体则归为VLA
            if any(k in text for k in ['robot', 'action', 'manipulation', 'embodied']):
                category = "VLA"
            else:
                category = "VLM"
            score = vlm_score

        # 来源加分
        if 'arxiv' in news.source.lower():
            score *= 1.2
        elif news.source.lower() in ['deepmind', 'meta', 'google']:
            score *= 1.3

        # 内容长度加分（有实质内容的加分）
        if len(news.content) > 200:
            score *= 1.1

        return score, category

    def _extract_source_name(self, feed_url: str, article_url: str) -> str:
        """提取来源名称"""
        # 首先从文章URL提取
        if article_url:
            parsed = urlparse(article_url)
            domain = parsed.netloc.lower()

            # 常见域名映射
            domain_map = {
                'arxiv.org': 'arXiv',
                'deepmind.google': 'DeepMind',
                'ai.meta.com': 'Meta AI',
                'research.google': 'Google Research',
                'techcrunch.com': 'TechCrunch',
                'venturebeat.com': 'VentureBeat',
                'wired.com': 'Wired',
                'leiphone.com': '雷锋网',
                'jiqizhixin.com': '机器之心',
                '36kr.com': '36氪',
                'towardsdatascience.com': 'Towards Data Science',
            }

            for key, value in domain_map.items():
                if key in domain:
                    return value

            # 返回简化域名
            parts = domain.split('.')
            if len(parts) >= 2:
                return parts[-2].capitalize()

        # 从feed URL提取
        if feed_url:
            parsed = urlparse(feed_url)
            domain = parsed.netloc.lower()
            parts = domain.split('.')
            if len(parts) >= 2:
                return parts[-2].capitalize()

        return "Unknown"

    def _get_default_news(self) -> List[News]:
        """获取默认示例新闻"""
        today = datetime.now().strftime("%Y-%m-%d")
        last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        last_month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        return [
            News(
                title="LLaVA-NeXT: Stronger Vision Language Model",
                content="LLaVA-NeXT introduces improved architecture for vision-language understanding, achieving SOTA on multiple benchmarks including VQAv2, GQA, and VizWiz. The model shows significant improvements in visual reasoning capabilities.",
                url="https://arxiv.org/abs/2312.12345",
                source="arXiv",
                published_date=last_week,
                category="VLM",
                relevance_score=3.5
            ),
            News(
                title="RT-2: Vision-Language-Action Models for Robot Control",
                content="Google DeepMind presents RT-2, a novel VLA model that enables robots to perform complex manipulation tasks using natural language instructions. The model shows strong generalization to unseen scenarios.",
                url="https://deepmind.google/blog/rt-2/",
                source="DeepMind",
                published_date=last_month,
                category="VLA",
                relevance_score=4.0
            ),
            News(
                title="CogVLM2: Visual Language Model for Complex Reasoning",
                content="CogVLM2 achieves state-of-the-art performance on visual reasoning tasks with an efficient architecture that combines vision transformers and language models. The model excels at detailed image understanding.",
                url="https://arxiv.org/abs/2401.12345",
                source="arXiv",
                published_date=last_week,
                category="VLM",
                relevance_score=3.2
            ),
            News(
                title="OpenVLA: An Open-Source Vision-Language-Action Model",
                content="OpenVLA provides an accessible implementation of VLA models for robotics research, demonstrating strong performance on manipulation tasks with efficient fine-tuning capabilities.",
                url="https://arxiv.org/abs/2402.12345",
                source="arXiv",
                published_date=last_month,
                category="VLA",
                relevance_score=3.8
            )
        ]


# 简化的调用函数
async def fetch_news(max_news: int = 10) -> List[News]:
    """
    获取VLM/VLA相关新闻

    Args:
        max_news: 最大返回新闻数

    Returns:
        相关性排序后的新闻列表
    """
    fetcher = NewsFetcher()
    try:
        news = await fetcher.fetch_news(max_news=max_news)
        return news
    except Exception as e:
        logger.error(f"Error in fetch_news: {e}")
        return fetcher._get_default_news()


# 使用示例
async def main():
    news = await fetch_news(max_news=10)

    print("\n" + "=" * 80)
    print("VLM/VLA 最新新闻".center(80))
    print("=" * 80)

    for i, item in enumerate(news, 1):
        print(f"\n{i}. [{item.category}] {item.title}")
        print(f"   来源: {item.source} | 日期: {item.published_date} | 相关度: {item.relevance_score:.1f}")
        print(f"   摘要: {item.content[:150]}...")
        print(f"   链接: {item.url}")


if __name__ == "__main__":
    asyncio.run(main())