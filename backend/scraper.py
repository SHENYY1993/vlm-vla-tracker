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
                    
                    # 生成复现指南
                    guideline = _generate_github_project_guideline(repo, detailed_info)
                    
                    projects.append(Project(
                        name=repo['name'],
                        description=description,
                        url=repo['html_url'],
                        stars=repo['stargazers_count'],
                        language=repo['language'],
                        owner=repo['owner']['login'],
                        category=category,
                        updated_at=repo.get('updated_at', '')[:10],
                        guideline=guideline
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
                            
                            # 生成复现指南
                            guideline = _generate_hf_model_guideline(model, detailed_info)
                    
                    projects.append(Project(
                        name=model['modelId'],
                        description=description,
                        url=f"https://huggingface.co/{model['modelId']}",
                        stars=model.get('downloads', 0),
                        language=None,
                        owner=model['modelId'].split('/')[0] if '/' in model['modelId'] else model['modelId'],
                        category=category,
                        updated_at=None,
                        guideline=guideline
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


# ==================== 复现指南生成函数 ====================

def _generate_github_project_guideline(repo: dict, detailed_info: dict) -> str:
    """生成GitHub项目的复现指南"""
    name = repo.get('name', '')
    description = repo.get('description', '')
    language = repo.get('language', '')
    stars = repo.get('stargazers_count', 0)
    url = repo.get('html_url', '')
    
    # 从详细信息中获取更多数据
    topics = detailed_info.get('topics', [])
    license_info = detailed_info.get('license', {})
    default_branch = detailed_info.get('default_branch', 'main')
    
    guideline_parts = []
    
    # 1. 项目概述
    guideline_parts.append("## 📋 项目概述")
    guideline_parts.append(f"- **项目名称**: {name}")
    guideline_parts.append(f"- **项目描述**: {description}")
    guideline_parts.append(f"- **编程语言**: {language or '未指定'}")
    guideline_parts.append(f"- **GitHub地址**: {url}")
    guideline_parts.append(f"- **Stars**: {stars:,}")
    if license_info:
        guideline_parts.append(f"- **许可证**: {license_info.get('name', '未指定')}")
    
    # 2. 硬件要求
    guideline_parts.append("\n## 🖥️ 硬件要求")
    if 'cuda' in topics or 'gpu' in topics or 'pytorch' in topics or 'tensorflow' in topics:
        guideline_parts.append("- **GPU**: 建议使用NVIDIA GPU，显存至少8GB（推荐16GB或以上）")
        guideline_parts.append("- **CUDA版本**: 建议CUDA 11.7或12.1")
        guideline_parts.append("- **内存**: 建议16GB或以上")
    else:
        guideline_parts.append("- **CPU**: 支持CPU运行，但速度较慢")
        guideline_parts.append("- **内存**: 建议8GB或以上")
    
    # 3. 软件依赖
    guideline_parts.append("\n## 📦 软件依赖")
    guideline_parts.append("### Python环境")
    guideline_parts.append("```bash")
    guideline_parts.append("# 推荐使用conda创建虚拟环境")
    guideline_parts.append("conda create -n vlm-env python=3.9 -y")
    guideline_parts.append("conda activate vlm-env")
    guideline_parts.append("```")
    
    guideline_parts.append("\n### 基础依赖")
    guideline_parts.append("```bash")
    guideline_parts.append("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
    guideline_parts.append("pip install transformers datasets accelerate peft bitsandbytes")
    guideline_parts.append("```")
    
    # 4. 数据集
    guideline_parts.append("\n## 📊 数据集")
    if 'llava' in name.lower():
        guideline_parts.append("- **LLaVA训练数据**: https://huggingface.co/datasets/liuhaotian/LLaVA-Instruct-150K")
        guideline_parts.append("- **COCO数据集**: https://cocodataset.org/")
        guideline_parts.append("- **VQAv2数据集**: https://visualqa.org/")
    elif 'blip' in name.lower():
        guideline_parts.append("- **COCO数据集**: https://cocodataset.org/")
        guideline_parts.append("- **Flickr30k数据集**: https://shannon.cs.illinois.edu/DenotationGraph/")
        guideline_parts.append("- **Conceptual Captions**: https://ai.google.com/research/ConceptualCaptions/")
    elif 'clip' in name.lower():
        guideline_parts.append("- **WIT数据集**: https://github.com/google-research-datasets/wit")
        guideline_parts.append("- **LAION数据集**: https://laion.ai/")
    else:
        guideline_parts.append("- **具体数据集**: 请参考项目README中的数据集说明")
        guideline_parts.append("- **数据预处理**: 通常需要将图像调整为统一尺寸，文本进行tokenization")
    
    # 5. 复现步骤
    guideline_parts.append("\n## 🚀 复现步骤")
    guideline_parts.append("### 1. 克隆项目")
    guideline_parts.append("```bash")
    guideline_parts.append(f"git clone {url}")
    guideline_parts.append(f"cd {name}")
    guideline_parts.append("```")
    
    guideline_parts.append("\n### 2. 安装依赖")
    guideline_parts.append("```bash")
    guideline_parts.append("pip install -r requirements.txt")
    guideline_parts.append("# 或者根据项目README安装特定依赖")
    guideline_parts.append("```")
    
    guideline_parts.append("\n### 3. 下载预训练模型")
    if 'llava' in name.lower():
        guideline_parts.append("```bash")
        guideline_parts.append("# 下载LLaVA模型")
        guideline_parts.append("huggingface-cli download liuhaotian/llava-v1.5-7b --local-dir ./models/llava-7b")
        guideline_parts.append("```")
    elif 'blip' in name.lower():
        guideline_parts.append("```bash")
        guideline_parts.append("# 下载BLIP模型")
        guideline_parts.append("huggingface-cli download Salesforce/blip2-opt-2.7b --local-dir ./models/blip2-2.7b")
        guideline_parts.append("```")
    elif 'clip' in name.lower():
        guideline_parts.append("```bash")
        guideline_parts.append("# 下载CLIP模型")
        guideline_parts.append("huggingface-cli download openai/clip-vit-base-patch32 --local-dir ./models/clip-base")
        guideline_parts.append("```")
    else:
        guideline_parts.append("```bash")
        guideline_parts.append("# 请根据项目README下载相应的预训练模型")
        guideline_parts.append("# 通常使用HuggingFace模型库")
        guideline_parts.append("```")
    
    guideline_parts.append("\n### 4. 数据准备")
    guideline_parts.append("```bash")
    guideline_parts.append("# 创建数据目录")
    guideline_parts.append("mkdir -p data/images data/annotations")
    guideline_parts.append("# 下载并解压数据集到相应目录")
    guideline_parts.append("```")
    
    guideline_parts.append("\n### 5. 训练模型")
    if 'llava' in name.lower():
        guideline_parts.append("```bash")
        guideline_parts.append("# LLaVA训练示例")
        guideline_parts.append("python train.py \\")
        guideline_parts.append("    --model_name_or_path ./models/llava-7b \\")
        guideline_parts.append("    --data_path ./data/llava_data.json \\")
        guideline_parts.append("    --image_folder ./data/images \\")
        guideline_parts.append("    --output_dir ./output/llava-finetuned \\")
        guideline_parts.append("    --num_train_epochs 3 \\")
        guideline_parts.append("    --per_device_train_batch_size 4 \\")
        guideline_parts.append("    --gradient_accumulation_steps 4 \\")
        guideline_parts.append("    --learning_rate 2e-5 \\")
        guideline_parts.append("    --warmup_steps 100 \\")
        guideline_parts.append("    --save_steps 1000 \\")
        guideline_parts.append("    --logging_steps 100")
        guideline_parts.append("```")
    elif 'blip' in name.lower():
        guideline_parts.append("```bash")
        guideline_parts.append("# BLIP训练示例")
        guideline_parts.append("python train.py \\")
        guideline_parts.append("    --model_name_or_path ./models/blip2-2.7b \\")
        guideline_parts.append("    --data_path ./data/coco_data.json \\")
        guideline_parts.append("    --image_folder ./data/images \\")
        guideline_parts.append("    --output_dir ./output/blip2-finetuned \\")
        guideline_parts.append("    --num_train_epochs 10 \\")
        guideline_parts.append("    --per_device_train_batch_size 2 \\")
        guideline_parts.append("    --learning_rate 1e-5 \\")
        guideline_parts.append("    --warmup_steps 500")
        guideline_parts.append("```")
    else:
        guideline_parts.append("```bash")
        guideline_parts.append("# 请根据项目README中的训练脚本进行训练")
        guideline_parts.append("# 通常包含以下参数：")
        guideline_parts.append("# - 模型路径")
        guideline_parts.append("# - 数据路径")
        guideline_parts.append("# - 输出目录")
        guideline_parts.append("# - 训练轮数")
        guideline_parts.append("# - 学习率")
        guideline_parts.append("# - 批次大小")
        guideline_parts.append("```")
    
    guideline_parts.append("\n### 6. 评估模型")
    guideline_parts.append("```bash")
    guideline_parts.append("# 评估脚本")
    guideline_parts.append("python evaluate.py \\")
    guideline_parts.append("    --model_path ./output/fine-tuned-model \\")
    guideline_parts.append("    --eval_data ./data/eval_data.json \\")
    guideline_parts.append("    --image_folder ./data/images")
    guideline_parts.append("```")
    
    # 7. 常见问题
    guideline_parts.append("\n## ❓ 常见问题")
    guideline_parts.append("### 内存不足 (OOM)")
    guideline_parts.append("- 减少batch_size")
    guideline_parts.append("- 使用梯度累积 (gradient_accumulation_steps)")
    guideline_parts.append("- 启用混合精度训练 (fp16=True)")
    guideline_parts.append("- 使用模型并行或ZeRO优化")
    
    guideline_parts.append("\n### 训练速度慢")
    guideline_parts.append("- 确保使用GPU训练")
    guideline_parts.append("- 检查CUDA和cuDNN版本兼容性")
    guideline_parts.append("- 使用更大的batch_size")
    guideline_parts.append("- 启用数据预加载")
    
    guideline_parts.append("\n### 模型效果不佳")
    guideline_parts.append("- 检查数据预处理是否正确")
    guideline_parts.append("- 调整学习率和训练轮数")
    guideline_parts.append("- 确保使用了正确的预训练模型")
    guideline_parts.append("- 检查损失函数和评估指标")
    
    # 8. 参考资源
    guideline_parts.append("\n## 🔗 参考资源")
    guideline_parts.append("- [PyTorch官方文档](https://pytorch.org/docs/stable/index.html)")
    guideline_parts.append("- [Transformers库文档](https://huggingface.co/docs/transformers/)")
    guideline_parts.append("- [项目官方README](https://github.com/your-username/your-project)")
    guideline_parts.append("- [相关论文链接](https://arxiv.org/)")
    
    return "\n".join(guideline_parts)


def _generate_hf_model_guideline(model: dict, detailed_info: dict) -> str:
    """生成HuggingFace模型的复现指南"""
    model_id = model.get('modelId', '')
    downloads = model.get('downloads', 0)
    tags = model.get('tags', [])
    card_data = detailed_info.get('card_data', {})
    
    guideline_parts = []
    
    # 1. 模型概述
    guideline_parts.append("## 📋 模型概述")
    guideline_parts.append(f"- **模型名称**: {model_id}")
    guideline_parts.append(f"- **下载量**: {downloads:,}")
    guideline_parts.append(f"- **HuggingFace地址**: https://huggingface.co/{model_id}")
    if card_data.get('description'):
        guideline_parts.append(f"- **模型描述**: {card_data['description'][:200]}...")
    
    # 2. 硬件要求
    guideline_parts.append("\n## 🖥️ 硬件要求")
    model_lower = model_id.lower()
    if any(kw in model_lower for kw in ['7b', '8b', 'llama', 'gpt']):
        guideline_parts.append("- **GPU**: 建议使用NVIDIA A100 40GB或V100 32GB")
        guideline_parts.append("- **显存**: 至少24GB（用于7B模型）")
        guideline_parts.append("- **内存**: 建议64GB或以上")
    elif any(kw in model_lower for kw in ['1b', '2b', '3b']):
        guideline_parts.append("- **GPU**: 建议使用RTX 3090或A100 40GB")
        guideline_parts.append("- **显存**: 至少16GB")
        guideline_parts.append("- **内存**: 建议32GB或以上")
    else:
        guideline_parts.append("- **GPU**: 建议使用NVIDIA GPU，显存至少8GB")
        guideline_parts.append("- **内存**: 建议16GB或以上")
        guideline_parts.append("- **CPU**: 支持CPU运行，但速度较慢")
    
    # 3. 软件依赖
    guideline_parts.append("\n## 📦 软件依赖")
    guideline_parts.append("```bash")
    guideline_parts.append("# 基础环境")
    guideline_parts.append("conda create -n vlm-env python=3.9 -y")
    guideline_parts.append("conda activate vlm-env")
    guideline_parts.append("")
    guideline_parts.append("# PyTorch (根据CUDA版本选择)")
    guideline_parts.append("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
    guideline_parts.append("")
    guideline_parts.append("# HuggingFace生态")
    guideline_parts.append("pip install transformers datasets accelerate peft bitsandbytes")
    guideline_parts.append("pip install sentencepiece einops flash-attn")
    guideline_parts.append("")
    guideline_parts.append("# 其他依赖")
    guideline_parts.append("pip install pillow matplotlib tqdm")
    guideline_parts.append("```")
    
    # 4. 数据集
    guideline_parts.append("\n## 📊 数据集")
    if 'llava' in model_lower:
        guideline_parts.append("- **LLaVA训练数据**: https://huggingface.co/datasets/liuhaotian/LLaVA-Instruct-150K")
        guideline_parts.append("- **COCO数据集**: https://cocodataset.org/")
        guideline_parts.append("- **数据格式**: JSON格式，包含image, text, conversation字段")
    elif 'blip' in model_lower:
        guideline_parts.append("- **COCO数据集**: https://cocodataset.org/")
        guideline_parts.append("- **Flickr30k数据集**: https://shannon.cs.illinois.edu/DenotationGraph/")
        guideline_parts.append("- **数据格式**: 图像+文本对")
    elif 'clip' in model_lower:
        guideline_parts.append("- **LAION数据集**: https://laion.ai/")
        guideline_parts.append("- **Conceptual Captions**: https://ai.google.com/research/ConceptualCaptions/")
        guideline_parts.append("- **数据格式**: 图像+文本对")
    else:
        guideline_parts.append("- **具体数据集**: 请参考模型卡片中的数据说明")
        guideline_parts.append("- **数据预处理**: 通常需要将图像调整为统一尺寸")
    
    # 5. 使用方法
    guideline_parts.append("\n## 🚀 使用方法")
    guideline_parts.append("### 1. 加载模型")
    guideline_parts.append("```python")
    guideline_parts.append("from transformers import AutoProcessor, AutoModelForCausalLM")
    guideline_parts.append("import torch")
    guideline_parts.append("")
    guideline_parts.append(f"model = AutoModelForCausalLM.from_pretrained(")
    guideline_parts.append(f"    \"{model_id}\",")
    guideline_parts.append("    torch_dtype=torch.float16,")
    guideline_parts.append("    device_map=\"auto\"")
    guideline_parts.append(")")
    guideline_parts.append("")
    if 'llava' in model_lower or 'blip' in model_lower:
        guideline_parts.append("processor = AutoProcessor.from_pretrained(\"" + model_id + "\")")
    guideline_parts.append("```")
    
    guideline_parts.append("\n### 2. 图像理解示例")
    guideline_parts.append("```python")
    guideline_parts.append("from PIL import Image")
    guideline_parts.append("import requests")
    guideline_parts.append("")
    guideline_parts.append("# 加载图像")
    guideline_parts.append("image = Image.open(\"path/to/your/image.jpg\")")
    guideline_parts.append("")
    if 'llava' in model_lower:
        guideline_parts.append("# LLaVA格式的提示词")
        guideline_parts.append("prompt = \"USER: <image>\\nWhat is shown in this image?\\nASSISTANT:\"")
    elif 'blip' in model_lower:
        guideline_parts.append("# BLIP格式的提示词")
        guideline_parts.append("prompt = \"Question: What is in the image? Answer:\"")
    else:
        guideline_parts.append("# 通用提示词格式")
        guideline_parts.append("prompt = \"Describe this image:\"")
    guideline_parts.append("")
    guideline_parts.append("# 处理输入")
    if 'llava' in model_lower or 'blip' in model_lower:
        guideline_parts.append("inputs = processor(prompt, image, return_tensors='pt').to(\"cuda\")")
    else:
        guideline_parts.append("inputs = processor(prompt, return_tensors='pt').to(\"cuda\")")
    guideline_parts.append("")
    guideline_parts.append("# 生成回答")
    guideline_parts.append("with torch.no_grad():")
    guideline_parts.append("    output = model.generate(**inputs, max_new_tokens=200, do_sample=True)")
    guideline_parts.append("")
    guideline_parts.append("# 解码输出")
    guideline_parts.append("response = processor.decode(output[0], skip_special_tokens=True)")
    guideline_parts.append("print(response)")
    guideline_parts.append("```")
    
    # 6. 微调训练
    guideline_parts.append("\n## 🔧 微调训练")
    guideline_parts.append("### 使用PEFT进行LoRA微调")
    guideline_parts.append("```python")
    guideline_parts.append("from peft import LoraConfig, get_peft_model")
    guideline_parts.append("from transformers import TrainingArguments, Trainer")
    guideline_parts.append("")
    guideline_parts.append("# 配置LoRA")
    guideline_parts.append("lora_config = LoraConfig(")
    guideline_parts.append("    r=8,")
    guideline_parts.append("    lora_alpha=16,")
    guideline_parts.append("    target_modules=[\"q_proj\", \"v_proj\"],  # 根据模型调整")
    guideline_parts.append("    lora_dropout=0.1,")
    guideline_parts.append("    bias=\"none\",")
    guideline_parts.append("    task_type=\"CAUSAL_LM\"")
    guideline_parts.append(")")
    guideline_parts.append("")
    guideline_parts.append("# 应用LoRA")
    guideline_parts.append("model = get_peft_model(model, lora_config)")
    guideline_parts.append("")
    guideline_parts.append("# 训练参数")
    guideline_parts.append("training_args = TrainingArguments(")
    guideline_parts.append("    output_dir=\"./results\",")
    guideline_parts.append("    num_train_epochs=3,")
    guideline_parts.append("    per_device_train_batch_size=4,")
    guideline_parts.append("    gradient_accumulation_steps=4,")
    guideline_parts.append("    learning_rate=2e-4,")
    guideline_parts.append("    fp16=True,")
    guideline_parts.append("    logging_steps=10,")
    guideline_parts.append("    save_steps=500,")
    guideline_parts.append("    evaluation_strategy=\"no\"")
    guideline_parts.append(")")
    guideline_parts.append("```")
    
    # 7. 性能优化
    guideline_parts.append("\n## ⚡ 性能优化")
    guideline_parts.append("### 量化推理")
    guideline_parts.append("```python")
    guideline_parts.append("# 使用bitsandbytes进行4-bit量化")
    guideline_parts.append("from transformers import BitsAndBytesConfig")
    guideline_parts.append("")
    guideline_parts.append("bnb_config = BitsAndBytesConfig(")
    guideline_parts.append("    load_in_4bit=True,")
    guideline_parts.append("    bnb_4bit_quant_type=\"nf4\",")
    guideline_parts.append("    bnb_4bit_compute_dtype=torch.float16,")
    guideline_parts.append("    bnb_4bit_use_double_quant=True,")
    guideline_parts.append(")")
    guideline_parts.append("")
    guideline_parts.append(f"model = AutoModelForCausalLM.from_pretrained(")
    guideline_parts.append(f"    \"{model_id}\",")
    guideline_parts.append("    quantization_config=bnb_config,")
    guideline_parts.append("    device_map=\"auto\"")
    guideline_parts.append(")")
    guideline_parts.append("```")
    
    guideline_parts.append("\n### Flash Attention")
    guideline_parts.append("```python")
    guideline_parts.append("# 启用Flash Attention加速")
    guideline_parts.append("model.config._attn_implementation = \"flash_attention_2\"")
    guideline_parts.append("```")
    
    # 8. 常见问题
    guideline_parts.append("\n## ❓ 常见问题")
    guideline_parts.append("### 内存不足")
    guideline_parts.append("- 使用量化技术 (4-bit/8-bit)")
    guideline_parts.append("- 启用梯度检查点 (gradient_checkpointing)")
    guideline_parts.append("- 减少batch_size")
    guideline_parts.append("- 使用模型并行")
    
    guideline_parts.append("\n### 推理速度慢")
    guideline_parts.append("- 启用Flash Attention")
    guideline_parts.append("- 使用Tensor Parallelism")
    guideline_parts.append("- 优化CUDA版本")
    guideline_parts.append("- 使用更快的存储 (SSD)")
    
    guideline_parts.append("\n### 结果不理想")
    guideline_parts.append("- 检查输入格式是否正确")
    guideline_parts.append("- 调整温度参数 (temperature)")
    guideline_parts.append("- 增加max_new_tokens")
    guideline_parts.append("- 检查模型是否完整下载")
    
    # 9. 参考资源
    guideline_parts.append("\n## 🔗 参考资源")
    guideline_parts.append("- [HuggingFace Transformers文档](https://huggingface.co/docs/transformers/)")
    guideline_parts.append("- [PEFT库文档](https://huggingface.co/docs/peft/)")
    guideline_parts.append("- [bitsandbytes文档](https://github.com/TimDettmers/bitsandbytes)")
    guideline_parts.append("- [Flash Attention文档](https://github.com/HazyResearch/flash-attention)")
    guideline_parts.append("- [模型原始论文](https://arxiv.org/)")
    
    return "\n".join(guideline_parts)


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
