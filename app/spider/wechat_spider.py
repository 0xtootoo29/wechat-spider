import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re
from typing import List, Dict, Optional
from fake_useragent import UserAgent

class WechatSpider:
    """微信公众号抓取引擎"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
    
    def test_account(self, wechat_id: str, gh_id: Optional[str] = None) -> Dict:
        """测试公众号抓取"""
        result = {
            "status": "success",
            "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "checks": {},
            "sample_articles": [],
            "suggestions": []
        }
        
        try:
            # 1. 连通性测试 - 通过搜狗微信搜索
            result["checks"]["connectivity"] = {"status": "running", "msg": "正在测试连接..."}
            
            search_url = f"https://weixin.sogou.com/weixin?type=1&query={wechat_id}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                result["checks"]["connectivity"] = {"status": "pass", "msg": "连接正常"}
            else:
                result["checks"]["connectivity"] = {"status": "failed", "msg": f"HTTP {response.status_code}"}
                result["status"] = "failed"
                return result
            
            # 2. ID 有效性测试
            result["checks"]["id_valid"] = {"status": "running", "msg": "正在验证ID..."}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            account_items = soup.find_all('li', class_='wx-rb')
            
            if not account_items:
                result["checks"]["id_valid"] = {"status": "warning", "msg": "未找到公众号，可能ID有误或未被收录"}
                result["suggestions"].append("建议检查微信号是否正确")
                result["suggestions"].append("新公众号可能需要等待搜狗收录（1-7天）")
            else:
                result["checks"]["id_valid"] = {"status": "pass", "msg": f"找到 {len(account_items)} 个相关公众号"}
            
            # 3. 文章抓取测试
            result["checks"]["article_fetch"] = {"status": "running", "msg": "正在测试文章抓取..."}
            
            # 获取文章列表页
            articles_url = f"https://weixin.sogou.com/weixin?type=2&query={wechat_id}"
            articles_response = self.session.get(articles_url, timeout=10)
            
            if articles_response.status_code == 200:
                articles_soup = BeautifulSoup(articles_response.text, 'html.parser')
                article_items = articles_soup.find_all('div', class_='txt-box')
                
                if article_items:
                    result["checks"]["article_fetch"] = {"status": "pass", "msg": f"成功发现 {len(article_items)} 篇文章"}
                    
                    # 4. 内容解析测试
                    result["checks"]["content_parse"] = {"status": "running", "msg": "正在测试内容解析..."}
                    
                    sample_articles = []
                    for i, item in enumerate(article_items[:3]):  # 取前3篇作为样本
                        try:
                            title_elem = item.find('h3')
                            title = title_elem.get_text(strip=True) if title_elem else "无标题"
                            
                            link_elem = item.find('a')
                            url = link_elem['href'] if link_elem else ""
                            
                            summary_elem = item.find('p', class_='txt-info')
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            sample_articles.append({
                                "title": title,
                                "url": url,
                                "summary": summary[:200] + "..." if len(summary) > 200 else summary
                            })
                        except Exception as e:
                            continue
                    
                    result["sample_articles"] = sample_articles
                    
                    if sample_articles:
                        result["checks"]["content_parse"] = {"status": "pass", "msg": "内容解析正常"}
                    else:
                        result["checks"]["content_parse"] = {"status": "warning", "msg": "部分文章解析失败"}
                else:
                    result["checks"]["article_fetch"] = {"status": "warning", "msg": "未发现文章"}
                    result["checks"]["content_parse"] = {"status": "skipped", "msg": "跳过解析"}
            else:
                result["checks"]["article_fetch"] = {"status": "failed", "msg": f"HTTP {articles_response.status_code}"}
                result["status"] = "failed"
            
            # 5. 反爬检测
            result["checks"]["anti_spider"] = {"status": "checking", "msg": "检测反爬机制..."}
            
            # 简单的反爬检测逻辑
            if "验证码" in response.text or "请稍后重试" in response.text:
                result["checks"]["anti_spider"] = {"status": "warning", "msg": "可能触发反爬机制"}
                result["suggestions"].append("建议降低抓取频率，每2小时一次")
                result["suggestions"].append("建议使用代理IP池")
            else:
                result["checks"]["anti_spider"] = {"status": "pass", "msg": "未检测到反爬限制"}
            
            # 生成建议
            if not result["suggestions"]:
                result["suggestions"].append("建议抓取频率：每小时一次")
                result["suggestions"].append("建议抓取深度：最近10篇")
                result["suggestions"].append("建议存储格式：Markdown")
            
        except requests.exceptions.Timeout:
            result["status"] = "failed"
            result["checks"]["connectivity"] = {"status": "failed", "msg": "连接超时"}
            result["suggestions"].append("网络连接不稳定，请检查网络")
        except Exception as e:
            result["status"] = "failed"
            result["checks"]["error"] = {"status": "failed", "msg": str(e)}
        
        return result
    
    def fetch_account(self, wechat_id: str, depth: int = 10) -> Dict:
        """抓取公众号文章"""
        result = {
            "account": wechat_id,
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "articles": []
        }
        
        try:
            # 通过搜狗搜索获取文章
            articles_url = f"https://weixin.sogou.com/weixin?type=2&query={wechat_id}"
            response = self.session.get(articles_url, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            article_items = soup.find_all('div', class_='txt-box')
            
            for i, item in enumerate(article_items[:depth]):
                try:
                    title_elem = item.find('h3')
                    title = title_elem.get_text(strip=True) if title_elem else "无标题"
                    
                    link_elem = item.find('a')
                    url = link_elem['href'] if link_elem else ""
                    
                    # 获取发布时间
                    time_elem = item.find('span', class_='s2')
                    publish_time = None
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)
                        # 解析时间文本
                        publish_time = self._parse_time(time_text)
                    
                    article = {
                        "title": title,
                        "url": url,
                        "publish_time": publish_time,
                        "source": "sogou"
                    }
                    
                    result["articles"].append(article)
                    
                    #  polite delay
                    time.sleep(0.5)
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            raise Exception(f"抓取失败: {str(e)}")
        
        return result
    
    def fetch_article_content(self, url: str) -> Dict:
        """抓取单篇文章内容"""
        try:
            # 搜狗微信的文章链接需要跳转
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title = soup.find('h2', class_='rich_media_title')
            title = title.get_text(strip=True) if title else "无标题"
            
            # 提取内容
            content_div = soup.find('div', id='js_content')
            content = ""
            if content_div:
                # 提取文本内容
                content = content_div.get_text('\n', strip=True)
            
            # 提取发布时间
            publish_time = None
            time_elem = soup.find('em', id='publish_time')
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                try:
                    publish_time = datetime.strptime(time_text, "%Y-%m-%d")
                except:
                    pass
            
            return {
                "title": title,
                "content": content,
                "publish_time": publish_time,
                "url": response.url
            }
            
        except Exception as e:
            raise Exception(f"抓取文章内容失败: {str(e)}")
    
    def _parse_time(self, time_text: str) -> Optional[datetime]:
        """解析时间文本"""
        try:
            # 处理相对时间
            if "分钟前" in time_text:
                minutes = int(re.search(r'(\d+)', time_text).group(1))
                return datetime.now() - timedelta(minutes=minutes)
            elif "小时前" in time_text:
                hours = int(re.search(r'(\d+)', time_text).group(1))
                return datetime.now() - timedelta(hours=hours)
            elif "昨天" in time_text:
                return datetime.now() - timedelta(days=1)
            elif "天前" in time_text:
                days = int(re.search(r'(\d+)', time_text).group(1))
                return datetime.now() - timedelta(days=days)
            else:
                # 尝试解析标准日期格式
                return datetime.strptime(time_text, "%Y-%m-%d")
        except:
            return None

from datetime import timedelta
