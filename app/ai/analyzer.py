import os
from typing import Dict, List
import json

class ArticleAnalyzer:
    """文章 AI 分析器（简化版，不依赖外部 API）"""
    
    def __init__(self):
        # 关键词库
        self.keyword_categories = {
            "科技": ["人工智能", "AI", "区块链", "大数据", "云计算", "5G", "物联网", "芯片", "算法", "科技", "互联网", "数字化", "智能", "创新", "技术"],
            "财经": ["股票", "基金", "投资", "理财", "经济", "金融", "市场", "企业", "利润", "营收", "财报", "上市", "融资", "并购", "商业"],
            "教育": ["教育", "学习", "学校", "学生", "考试", "课程", "培训", "知识", "学术", "研究", "大学", "教师", "教学"],
            "健康": ["健康", "医疗", "医院", "医生", "疾病", "养生", "健身", "营养", "心理", "治疗", "药品", "保健"],
            "娱乐": ["电影", "音乐", "明星", "综艺", "娱乐", "八卦", "影视", "演唱会", "剧集", "娱乐", "八卦", "爆料"],
            "生活": ["美食", "旅游", "家居", "时尚", "育儿", "宠物", "生活", "日常", "情感", "婚姻", "家庭"],
            "时政": ["政策", "政府", "国家", "政治", "外交", "军事", "社会", "民生", "法规", "改革"]
        }
        
        # 情感词库
        self.sentiment_words = {
            "positive": ["好", "优秀", "成功", "增长", "突破", "创新", "领先", "优势", "机遇", "利好", "赞赏", "支持", "喜欢", "满意", "惊喜"],
            "negative": ["差", "失败", "下降", "亏损", "问题", "危机", "风险", "劣势", "挑战", "利空", "批评", "反对", "讨厌", "失望", "担忧"]
        }
    
    def analyze(self, content: str) -> Dict:
        """分析文章内容"""
        if not content or len(content) < 10:
            return {
                "summary": "内容太短，无法分析",
                "keywords": [],
                "category": "未分类",
                "sentiment": "中性"
            }
        
        # 1. 生成摘要（取前200字）
        summary = content[:200] + "..." if len(content) > 200 else content
        summary = summary.replace("\n", " ").strip()
        
        # 2. 提取关键词
        keywords = self._extract_keywords(content)
        
        # 3. 分类
        category = self._classify(content)
        
        # 4. 情感分析
        sentiment = self._analyze_sentiment(content)
        
        return {
            "summary": summary,
            "keywords": keywords,
            "category": category,
            "sentiment": sentiment
        }
    
    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        keywords = []
        content_lower = content.lower()
        
        # 统计各分类关键词出现次数
        category_scores = {}
        for category, words in self.keyword_categories.items():
            score = 0
            for word in words:
                count = content.count(word)
                score += count
            category_scores[category] = score
        
        # 返回得分最高的分类相关词
        top_category = max(category_scores, key=category_scores.get)
        if category_scores[top_category] > 0:
            # 返回该分类中出现的关键词
            for word in self.keyword_categories[top_category]:
                if word in content and word not in keywords:
                    keywords.append(word)
                    if len(keywords) >= 5:
                        break
        
        return keywords[:5]
    
    def _classify(self, content: str) -> str:
        """文章分类"""
        scores = {}
        
        for category, keywords in self.keyword_categories.items():
            score = 0
            for keyword in keywords:
                score += content.count(keyword)
            scores[category] = score
        
        # 返回得分最高的分类
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "其他"
    
    def _analyze_sentiment(self, content: str) -> str:
        """情感分析"""
        positive_count = 0
        negative_count = 0
        
        for word in self.sentiment_words["positive"]:
            positive_count += content.count(word)
        
        for word in self.sentiment_words["negative"]:
            negative_count += content.count(word)
        
        if positive_count > negative_count * 1.5:
            return "正面"
        elif negative_count > positive_count * 1.5:
            return "负面"
        else:
            return "中性"
    
    def generate_report(self, articles: List[Dict]) -> Dict:
        """生成分析报告"""
        if not articles:
            return {"error": "没有文章数据"}
        
        # 统计分类分布
        category_dist = {}
        sentiment_dist = {"正面": 0, "中性": 0, "负面": 0}
        all_keywords = []
        
        for article in articles:
            # 分类统计
            cat = article.get("category", "其他")
            category_dist[cat] = category_dist.get(cat, 0) + 1
            
            # 情感统计
            sent = article.get("sentiment", "中性")
            sentiment_dist[sent] = sentiment_dist.get(sent, 0) + 1
            
            # 关键词收集
            keywords = article.get("keywords", [])
            if isinstance(keywords, str):
                keywords = json.loads(keywords)
            all_keywords.extend(keywords)
        
        # 统计热门关键词
        keyword_counts = {}
        for kw in all_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_articles": len(articles),
            "category_distribution": category_dist,
            "sentiment_distribution": sentiment_dist,
            "top_keywords": top_keywords,
            "date_range": {
                "start": articles[0].get("publish_time", "Unknown"),
                "end": articles[-1].get("publish_time", "Unknown")
            }
        }
