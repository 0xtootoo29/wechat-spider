from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import os
import json
import asyncio

from ..models import SessionLocal, Task, TaskLog, Article, OfficialAccount, AuthCredential, DownloadQueue
from ..spider.wechat_spider import WechatSpider
from ..spider.article_fetcher import ArticleFetcher
from ..spider.content_processor import ContentProcessor
from ..auth.credential_manager import CredentialManager
from ..ai.analyzer import ArticleAnalyzer


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.spider = WechatSpider()
        self.credential_manager = CredentialManager()
        self.content_processor = ContentProcessor()
        self.analyzer = ArticleAnalyzer()
        self._load_tasks()

    def get_credential_for_account(self, db, account_nickname: str):
        """获取公众号对应的认证信息"""
        # 首先尝试从 AuthCredential 表中获取
        credential = db.query(AuthCredential).filter(
            AuthCredential.account_nickname == account_nickname,
            AuthCredential.is_active == True
        ).first()

        if credential and not self.is_credential_expired(credential):
            return credential

        return None

    def is_credential_expired(self, credential: AuthCredential) -> bool:
        """检查认证信息是否过期"""
        from datetime import datetime
        return datetime.now() > credential.expires_at

    def _load_tasks(self):
        """从数据库加载所有激活的任务"""
        db = SessionLocal()
        try:
            tasks = db.query(Task).filter(Task.status == "active").all()
            for task in tasks:
                self._schedule_task(task)
        finally:
            db.close()

    def _schedule_task(self, task):
        """调度单个任务"""
        if task.schedule_type == "realtime":
            return
        elif task.schedule_type == "hourly":
            trigger = CronTrigger(minute=0)
        elif task.schedule_type == "daily":
            hour, minute = map(int, task.schedule_time.split(":"))
            trigger = CronTrigger(hour=hour, minute=minute)
        elif task.schedule_type == "weekly":
            hour, minute = map(int, task.schedule_time.split(":"))
            trigger = CronTrigger(day_of_week=0, hour=hour, minute=minute)
        else:
            return

        job_id = f"task_{task.id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        self.scheduler.add_job(
            func=self._execute_task,
            trigger=trigger,
            id=job_id,
            args=[task.id],
            replace_existing=True
        )

    def _execute_task(self, task_id):
        """执行任务"""
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task or task.status != "active":
                return

            log = TaskLog(
                task_id=task_id,
                status="running",
                start_time=datetime.now()
            )
            db.add(log)
            db.commit()

            accounts = []
            if task.account_id:
                account = db.query(OfficialAccount).filter(OfficialAccount.id == task.account_id).first()
                if account:
                    accounts.append(account)

            total_articles = 0
            errors = []

            for account in accounts:
                try:
                    # 检查是否有认证信息可用
                    credential = self.get_credential_for_account(db, account.name)
                    if credential:
                        # 使用新的 article_fetcher 获取文章列表
                        fetcher = ArticleFetcher(credential.cookie, credential.token)

                        # 根据任务类型决定执行方式
                        if hasattr(task, 'fetch_full_history') and task.fetch_full_history:
                            # 获取全部历史文章
                            articles = asyncio.run(fetcher.get_all_articles(
                                nickname=account.name,
                                progress_callback=lambda current, total: print(f"获取进度: {current}/{total}")
                            ))

                            # 将文章添加到下载队列
                            for article in articles:
                                url = article.get('link', article.get('app_url'))
                                if url:
                                    queue_item = DownloadQueue(
                                        article_url=url,
                                        account_nickname=account.name,
                                        status="pending"
                                    )
                                    db.add(queue_item)

                        else:
                            # 使用原有方式获取最近文章
                            result = self.spider.fetch_account(account.wechat_id, task.fetch_depth)

                            for article_data in result.get("articles", []):
                                existing = db.query(Article).filter(Article.url == article_data["url"]).first()
                                if existing:
                                    continue

                                article = Article(
                                    title=article_data["title"],
                                    author=account.name,
                                    url=article_data["url"],
                                    publish_time=article_data.get("publish_time"),
                                    account_id=account.id,
                                    task_id=task_id
                                )

                                # AI 分析
                                if task.ai_analysis and article.content:
                                    try:
                                        analysis = self.analyzer.analyze(article.content)
                                        article.ai_summary = analysis.get("summary")
                                        article.keywords = json.dumps(analysis.get("keywords", []), ensure_ascii=False)
                                        article.sentiment = analysis.get("sentiment")
                                        article.category = analysis.get("category")
                                    except Exception as e:
                                        print(f"AI分析失败: {e}")

                                if task.storage_format == "markdown":
                                    self._save_as_markdown(article, task.storage_path)

                                total_articles += 1

                    else:
                        # 如果没有认证信息，使用原有的搜狗方式（仅获取URL列表）
                        result = self.spider.fetch_account(account.wechat_id, task.fetch_depth)

                        for article_data in result.get("articles", []):
                            existing = db.query(Article).filter(Article.url == article_data["url"]).first()
                            if existing:
                                continue

                            article = Article(
                                title=article_data["title"],
                                author=account.name,
                                url=article_data["url"],
                                publish_time=article_data.get("publish_time"),
                                account_id=account.id,
                                task_id=task_id
                            )

                            # AI 分析
                            if task.ai_analysis and article.content:
                                try:
                                    analysis = self.analyzer.analyze(article.content)
                                    article.ai_summary = analysis.get("summary")
                                    article.keywords = json.dumps(analysis.get("keywords", []), ensure_ascii=False)
                                    article.sentiment = analysis.get("sentiment")
                                    article.category = analysis.get("category")
                                except Exception as e:
                                    print(f"AI分析失败: {e}")

                            if task.storage_format == "markdown":
                                self._save_as_markdown(article, task.storage_path)

                            total_articles += 1

                except Exception as e:
                    errors.append(f"{account.name}: {str(e)}")

            log.status = "success" if not errors else "partial"
            log.articles_count = total_articles
            log.end_time = datetime.now()
            if errors:
                log.error_msg = "\n".join(errors)

            task.last_run = datetime.now()
            db.commit()

        except Exception as e:
            log.status = "failed"
            log.error_msg = str(e)
            log.end_time = datetime.now()
            db.commit()
        finally:
            db.close()

    def execute_full_history_task(self, task_id, account_nickname: str):
        """执行获取全部历史文章的任务"""
        db = SessionLocal()
        try:
            # 获取认证信息
            credential = self.get_credential_for_account(db, account_nickname)
            if not credential:
                raise ValueError(f"未找到 {account_nickname} 的有效认证信息")

            # 创建文章获取器
            fetcher = ArticleFetcher(credential.cookie, credential.token)

            # 获取全部文章列表
            articles = asyncio.run(fetcher.get_all_articles(
                nickname=account_nickname,
                progress_callback=lambda current, total: self._update_task_progress(task_id, current, total)
            ))

            # 将所有文章URL添加到下载队列
            queued_count = 0
            for article in articles:
                url = article.get('link', article.get('app_url'))
                if url:
                    # 检查队列中是否已存在
                    existing = db.query(DownloadQueue).filter(
                        DownloadQueue.article_url == url,
                        DownloadQueue.account_nickname == account_nickname
                    ).first()

                    if not existing:
                        queue_item = DownloadQueue(
                            article_url=url,
                            account_nickname=account_nickname,
                            status="pending"
                        )
                        db.add(queue_item)
                        queued_count += 1

            db.commit()
            print(f"已将 {queued_count} 篇文章添加到下载队列")

            # 启动下载队列处理器
            self.process_download_queue(db, account_nickname)

        except Exception as e:
            print(f"执行完整历史任务失败: {e}")
            raise
        finally:
            db.close()

    def _update_task_progress(self, task_id: str, current: int, total: int):
        """更新任务进度"""
        # 这里可以更新任务进度，可能通过WebSocket或其他方式通知前端
        progress_percent = (current / total) * 100
        print(f"任务 {task_id} 进度: {current}/{total} ({progress_percent:.1f}%)")

    def process_download_queue(self, db, account_nickname: str = None):
        """处理下载队列"""
        query = db.query(DownloadQueue).filter(DownloadQueue.status == "pending")
        if account_nickname:
            query = query.filter(DownloadQueue.account_nickname == account_nickname)

        pending_items = query.all()

        processed_count = 0
        for item in pending_items:
            try:
                # 更新状态为正在下载
                item.status = "downloading"
                db.commit()

                # 使用内容处理器处理文章
                result = asyncio.run(self.content_processor.process_article(
                    url=item.article_url,
                    account_name=item.account_nickname
                ))

                # 创建文章记录
                article = Article(
                    title=result["title"],
                    author=result["author"],
                    url=item.article_url,
                    publish_time=result.get("publish_time"),
                    content=result["content"],  # 存储 Markdown 内容
                    html_content=result["html_content"],
                    markdown_content=result["content"],
                    images_count=result["images_count"],
                    account_id=None,  # 需要根据实际情况关联到具体公众号
                    task_id=None  # 关联到相应任务
                )

                db.add(article)

                # 更新队列状态
                item.status = "completed"
                item.completed_at = datetime.now()
                processed_count += 1

                db.commit()

            except Exception as e:
                item.status = "failed"
                item.error_message = str(e)
                item.retry_count += 1
                db.commit()

                # 如果重试次数过多，可以考虑跳过或特殊处理
                if item.retry_count > 3:
                    print(f"文章 {item.article_url} 重试 {item.retry_count} 次后仍失败: {e}")

        print(f"下载队列处理完成，共处理 {processed_count} 篇文章")

    def _save_as_markdown(self, article, storage_path):
        """保存文章为 Markdown"""
        date_dir = datetime.now().strftime("%Y%m")
        save_dir = os.path.join(storage_path, date_dir)
        os.makedirs(save_dir, exist_ok=True)

        safe_title = "".join(c for c in article.title if c.isalnum() or c in (' ', '-', '_'))[:50]
        filename = f"{datetime.now().strftime('%Y%m%d')}_{safe_title}.md"
        filepath = os.path.join(save_dir, filename)

        md_content = f"""---
title: {article.title}
author: {article.author}
publish_time: {article.publish_time.strftime('%Y-%m-%d %H:%M:%S') if article.publish_time else 'Unknown'}
url: {article.url}
task_id: {article.task_id}
fetch_time: {article.fetch_time.strftime('%Y-%m-%d %H:%M:%S')}
---

# {article.title}

[原文链接]({article.url})"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        article.file_path = filepath

    def add_task(self, task):
        """添加新任务"""
        if task.status == "active":
            self._schedule_task(task)

    def remove_task(self, task_id):
        """移除任务"""
        job_id = f"task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    def run_task_now(self, task_id):
        """立即执行任务"""
        self._execute_task(task_id)