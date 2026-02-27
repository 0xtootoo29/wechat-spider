from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import os
import json

from models import SessionLocal, Task, TaskLog, Article, OfficialAccount
from spider.wechat_spider import WechatSpider
from ai.analyzer import ArticleAnalyzer

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.spider = WechatSpider()
        self.analyzer = ArticleAnalyzer()
        self._load_tasks()
    
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

[原文链接]({article.url})
"""
        
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
