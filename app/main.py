import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

from models import init_db, get_db, OfficialAccount, AccountGroup, Task, TaskLog, Article
from spider.wechat_spider import WechatSpider
from scheduler.task_scheduler import TaskScheduler

# 初始化数据库
init_db()

app = FastAPI(title="WeChat Spider Pro", version="1.0.0")

# 初始化任务调度器
task_scheduler = TaskScheduler()

# 静态文件和模板
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# 首页
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ============ 公众号管理 API ============

class AccountCreate(BaseModel):
    name: str
    wechat_id: str
    gh_id: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None

class AccountResponse(BaseModel):
    id: str
    name: str
    wechat_id: str
    gh_id: Optional[str]
    description: Optional[str]
    category: Optional[str]
    status: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

@app.post("/api/accounts", response_model=AccountResponse)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    """添加公众号"""
    db_account = OfficialAccount(**account.dict())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.get("/api/accounts", response_model=List[AccountResponse])
def list_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取公众号列表"""
    accounts = db.query(OfficialAccount).offset(skip).limit(limit).all()
    return accounts

@app.get("/api/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: str, db: Session = Depends(get_db)):
    """获取公众号详情"""
    account = db.query(OfficialAccount).filter(OfficialAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    return account

@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: str, db: Session = Depends(get_db)):
    """删除公众号"""
    account = db.query(OfficialAccount).filter(OfficialAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    db.delete(account)
    db.commit()
    return {"message": "删除成功"}

# ============ 公众号测试 API ============

class TestResult(BaseModel):
    status: str
    test_time: str
    checks: dict
    sample_articles: List[dict]
    suggestions: List[str]

@app.post("/api/accounts/test", response_model=TestResult)
def test_account(account: AccountCreate):
    """测试公众号抓取"""
    spider = WechatSpider()
    result = spider.test_account(account.wechat_id, account.gh_id)
    return result

# ============ 任务管理 API ============

class TaskCreate(BaseModel):
    name: str
    account_id: Optional[str] = None
    group_id: Optional[str] = None
    schedule_type: str = "daily"  # realtime/hourly/daily/weekly
    schedule_time: str = "08:00"
    fetch_depth: int = 10
    fetch_days: int = 7
    storage_format: str = "markdown"
    storage_path: str = "./data/articles"
    ai_analysis: bool = True

class TaskResponse(BaseModel):
    id: str
    name: str
    account_id: Optional[str]
    schedule_type: str
    schedule_time: str
    fetch_depth: int
    status: str
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

@app.post("/api/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """创建任务"""
    db_task = Task(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # 添加到调度器
    task_scheduler.add_task(db_task)
    
    return db_task

@app.get("/api/tasks", response_model=List[TaskResponse])
def list_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取任务列表"""
    tasks = db.query(Task).offset(skip).limit(limit).all()
    return tasks

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取执行日志
    logs = db.query(TaskLog).filter(TaskLog.task_id == task_id).order_by(TaskLog.start_time.desc()).limit(10).all()
    
    return {
        "task": task,
        "logs": logs
    }

@app.post("/api/tasks/{task_id}/run")
def run_task(task_id: str, db: Session = Depends(get_db)):
    """手动执行任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 使用调度器立即执行
    task_scheduler.run_task_now(task_id)
    
    return {"message": "任务已启动"}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 从调度器移除
    task_scheduler.remove_task(task_id)
    
    db.delete(task)
    db.commit()
    return {"message": "删除成功"}

# ============ 文章管理 API ============

@app.get("/api/articles")
def list_articles(
    account_id: Optional[str] = None,
    task_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取文章列表"""
    query = db.query(Article)
    if account_id:
        query = query.filter(Article.account_id == account_id)
    if task_id:
        query = query.filter(Article.task_id == task_id)
    
    articles = query.order_by(Article.fetch_time.desc()).offset(skip).limit(limit).all()
    return articles

@app.get("/api/articles/{article_id}")
def get_article(article_id: str, db: Session = Depends(get_db)):
    """获取文章详情"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 读取文件内容
    content = ""
    if article.file_path and os.path.exists(article.file_path):
        with open(article.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    
    return {
        "article": article,
        "content": content
    }

# ============ 统计 API ============

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """获取统计数据"""
    total_accounts = db.query(OfficialAccount).count()
    total_tasks = db.query(Task).count()
    total_articles = db.query(Article).count()
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_articles = db.query(Article).filter(Article.fetch_time >= today).count()
    
    recent_logs = db.query(TaskLog).order_by(TaskLog.start_time.desc()).limit(5).all()
    
    return {
        "total_accounts": total_accounts,
        "total_tasks": total_tasks,
        "total_articles": total_articles,
        "today_articles": today_articles,
        "recent_logs": recent_logs
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
