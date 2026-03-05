"""
微信公众号文章内容处理器
功能：HTML 获取 → 图片下载 → Markdown 生成
"""
import asyncio
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md


class ContentProcessor:
    """微信公众号文章内容处理器"""

    def __init__(self, base_dir: str = "data/articles"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # HTTP 客户端配置
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://mp.weixin.qq.com/",
        }
        self.timeout = httpx.Timeout(30.0)

    async def process_article(
        self,
        url: str,
        account_name: str,
        save_html: bool = True
    ) -> Dict:
        """
        处理单篇文章：获取 HTML → 下载图片 → 生成 Markdown

        Args:
            url: 文章 URL
            account_name: 公众号名称
            save_html: 是否保存原始 HTML

        Returns:
            {
                "title": str,
                "author": str,
                "publish_time": str,
                "content": str,  # Markdown 内容
                "html_content": str,  # 原始 HTML
                "article_dir": str,  # 文章目录路径
                "markdown_path": str,  # Markdown 文件路径
                "images_count": int,  # 图片数量
            }
        """
        # 1. 获取 HTML
        html = await self._fetch_html(url)

        # 2. 提取元数据
        metadata = self._extract_metadata(html)

        # 3. 提取正文内容
        content_html = self._extract_content(html)

        # 4. 创建文章目录
        article_dir = self._create_article_dir(account_name, metadata["title"], metadata["publish_time"])

        # 5. 下载图片
        images_map = await self._download_images(content_html, article_dir)

        # 6. 替换图片链接为本地路径
        content_html_local = self._replace_image_urls(content_html, images_map)

        # 7. 转换为 Markdown
        markdown_content = self._html_to_markdown(content_html_local)

        # 8. 生成完整的 Markdown 文件（带 frontmatter）
        full_markdown = self._build_markdown_file(metadata, markdown_content, url)

        # 9. 保存文件
        markdown_path = article_dir / "article.md"
        markdown_path.write_text(full_markdown, encoding="utf-8")

        if save_html:
            html_path = article_dir / "article.html"
            html_path.write_text(html, encoding="utf-8")

        return {
            "title": metadata["title"],
            "author": metadata["author"],
            "publish_time": metadata["publish_time"],
            "content": markdown_content,
            "html_content": html,
            "article_dir": str(article_dir),
            "markdown_path": str(markdown_path),
            "images_count": len(images_map),
        }

    async def _fetch_html(self, url: str) -> str:
        """获取文章 HTML"""
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def _extract_metadata(self, html: str) -> Dict:
        """提取文章元数据"""
        soup = BeautifulSoup(html, "lxml")

        # 标题
        title_tag = soup.find("h1", class_="rich_media_title")
        title = title_tag.get_text(strip=True) if title_tag else "未知标题"

        # 作者
        author_tag = soup.find("a", class_="rich_media_meta_link")
        author = author_tag.get_text(strip=True) if author_tag else "未知作者"

        # 发布时间
        time_tag = soup.find("em", id="publish_time")
        publish_time = time_tag.get_text(strip=True) if time_tag else ""

        return {
            "title": self._sanitize_filename(title),
            "author": author,
            "publish_time": publish_time,
        }

    def _extract_content(self, html: str) -> str:
        """提取文章正文内容"""
        soup = BeautifulSoup(html, "lxml")

        # 尝试多种可能的微信文章正文选择器
        content_selectors = [
            "div#js_content",  # 主要选择器
            "div.rich_media_content",  # 备用选择器
            ".rich_media_content",  # 备用选择器
            "#content",  # 通用选择器
            ".content"  # 通用选择器
        ]

        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                return str(content_div)

        # 如果以上选择器都失败，则抛出异常
        raise ValueError(f"无法找到文章正文内容，尝试了以下选择器: {content_selectors}")

    async def _download_images(self, html: str, article_dir: Path) -> Dict[str, str]:
        """
        异步下载所有图片

        Returns:
            {原始URL: 本地相对路径}
        """
        soup = BeautifulSoup(html, "lxml")
        img_tags = soup.find_all("img")

        if not img_tags:
            return {}

        # 创建图片目录
        images_dir = article_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # 提取所有图片 URL
        image_urls = []
        for img in img_tags:
            src = img.get("data-src") or img.get("src")
            if src and src.startswith("http"):
                image_urls.append(src)

        # 并发下载
        tasks = [
            self._download_single_image(url, images_dir, idx)
            for idx, url in enumerate(image_urls)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 构建映射表
        images_map = {}
        for url, result in zip(image_urls, results):
            if isinstance(result, str):  # 成功返回本地路径
                images_map[url] = result

        return images_map

    async def _download_single_image(
        self, url: str, images_dir: Path, idx: int
    ) -> str:
        """下载单张图片"""
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                # 确定文件扩展名
                content_type = response.headers.get("content-type", "")
                if "jpeg" in content_type or "jpg" in content_type:
                    ext = "jpg"
                elif "png" in content_type:
                    ext = "png"
                elif "gif" in content_type:
                    ext = "gif"
                elif "webp" in content_type:
                    ext = "webp"
                else:
                    ext = "jpg"  # 默认

                # 保存文件
                filename = f"img_{idx:03d}.{ext}"
                filepath = images_dir / filename
                filepath.write_bytes(response.content)

                # 返回相对路径
                return f"images/{filename}"

        except Exception as e:
            print(f"下载图片失败 {url}: {e}")
            return ""

    def _replace_image_urls(self, html: str, images_map: Dict[str, str]) -> str:
        """替换图片链接为本地路径"""
        soup = BeautifulSoup(html, "lxml")

        for img in soup.find_all("img"):
            src = img.get("data-src") or img.get("src")
            if src in images_map:
                img["src"] = images_map[src]
                # 移除 data-src 属性
                if img.get("data-src"):
                    del img["data-src"]

        return str(soup)

    def _html_to_markdown(self, html: str) -> str:
        """HTML 转 Markdown"""
        return md(html, heading_style="ATX", strip=["script", "style"])

    def _build_markdown_file(self, metadata: Dict, content: str, url: str) -> str:
        """生成带 YAML frontmatter 的 Markdown 文件"""
        frontmatter = f"""---
title: {metadata['title']}
author: {metadata['author']}
publish_time: {metadata['publish_time']}
url: {url}
downloaded_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

"""
        return frontmatter + content

    def _create_article_dir(
        self, account_name: str, title: str, publish_time: str
    ) -> Path:
        """创建文章目录"""
        # 从发布时间提取日期
        date_str = ""
        if publish_time:
            # 尝试解析日期（格式：2024-03-05）
            match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", publish_time)
            if match:
                date_str = f"{match.group(1)}{match.group(2):0>2}{match.group(3):0>2}"

        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")

        # 目录名：日期_标题
        dir_name = f"{date_str}_{title[:50]}"  # 限制长度
        article_dir = self.base_dir / account_name / dir_name
        article_dir.mkdir(parents=True, exist_ok=True)

        return article_dir

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # 移除或替换非法字符
        filename = re.sub(r'[<>:"/\\|?*]', "", filename)
        filename = filename.strip()
        return filename or "untitled"

