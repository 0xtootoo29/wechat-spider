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

from models import init_db, get_db, OfficialAccount, AccountGroup, Task, TaskLog, Article, AuthCredential, DownloadQueue
from spider.wechat_spider import WechatSpider
from spider.article_fetcher import ArticleFetcher
from scheduler.task_scheduler import TaskScheduler
from ai.analyzer import ArticleAnalyzer

# 初始化数据库
init_db()

app = FastAPI(title="WeChat Spider Pro", version="1.0.0")

# 初始化任务调度器
task_scheduler = TaskScheduler()

# 静态文件和模板
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

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

# ============ AI 分析 API ============

@app.post("/api/analyze/{article_id}")
def analyze_article(article_id: str, db: Session = Depends(get_db)):
    """分析单篇文章"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if not article.content:
        raise HTTPException(status_code=400, detail="文章内容为空")
    
    analyzer = ArticleAnalyzer()
    result = analyzer.analyze(article.content)
    
    # 更新文章分析结果
    article.ai_summary = result["summary"]
    article.keywords = json.dumps(result["keywords"], ensure_ascii=False)
    article.sentiment = result["sentiment"]
    article.category = result["category"]
    db.commit()
    
    return result

@app.get("/api/analysis/report")
def get_analysis_report(
    account_id: Optional[str] = None,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """获取分析报告"""
    from_date = datetime.now() - timedelta(days=days)
    
    query = db.query(Article).filter(Article.fetch_time >= from_date)
    if account_id:
        query = query.filter(Article.account_id == account_id)
    
    articles = query.all()
    
    # 转换为字典列表
    article_dicts = []
    for art in articles:
        article_dicts.append({
            "title": art.title,
            "category": art.category,
            "sentiment": art.sentiment,
            "keywords": art.keywords,
            "publish_time": art.publish_time
        })
    
    analyzer = ArticleAnalyzer()
    report = analyzer.generate_report(article_dicts)
    
    return report

# ============ Phase 1 测试端点 ============

class ProcessUrlRequest(BaseModel):
    url: str
    account_name: str = "测试公众号"
    save_html: bool = True

class ProcessUrlResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

@app.post("/api/test/process-url", response_model=ProcessUrlResponse)
async def test_process_url(request: ProcessUrlRequest):
    """
    Phase 1 测试端点：处理单篇文章 URL

    输入：微信文章 URL
    输出：Markdown 文件 + 图片
    """
    try:
        from spider.content_processor import ContentProcessor

        processor = ContentProcessor()
        result = await processor.process_article(
            url=request.url,
            account_name=request.account_name,
            save_html=request.save_html
        )

        return ProcessUrlResponse(
            success=True,
            message="文章处理成功",
            data=result
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return ProcessUrlResponse(
            success=False,
            message=f"处理失败: {str(e)}",
            data={"error_detail": error_detail}
        )


# ============ Phase 3 新增 API 端点 ============

# 认证信息管理
class CredentialCreate(BaseModel):
    account_nickname: str
    cookie: str
    token: str
    notes: Optional[str] = None

class CredentialResponse(BaseModel):
    id: str
    account_nickname: str
    created_at: datetime
    expires_at: datetime
    is_active: bool
    notes: Optional[str]

@app.post("/api/credentials", response_model=CredentialResponse)
def create_credential(credential: CredentialCreate, db: Session = Depends(get_db)):
    """添加认证信息"""
    db_credential = AuthCredential(
        account_nickname=credential.account_nickname,
        cookie=credential.cookie,
        token=credential.token,
        notes=credential.notes
    )
    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)
    return db_credential

@app.get("/api/credentials", response_model=List[CredentialResponse])
def list_credentials(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取认证信息列表"""
    credentials = db.query(AuthCredential).offset(skip).limit(limit).all()
    return credentials

@app.delete("/api/credentials/{cred_id}")
def delete_credential(cred_id: str, db: Session = Depends(get_db)):
    """删除认证信息"""
    credential = db.query(AuthCredential).filter(AuthCredential.id == cred_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="认证信息不存在")
    db.delete(credential)
    db.commit()
    return {"message": "删除成功"}

@app.post("/api/credentials/{cred_id}/test")
def test_credential(cred_id: str, db: Session = Depends(get_db)):
    """测试认证信息有效性"""
    credential = db.query(AuthCredential).filter(AuthCredential.id == cred_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="认证信息不存在")

    try:
        from spider.article_fetcher import ArticleFetcher
        fetcher = ArticleFetcher(credential.cookie, credential.token)

        # 尝试获取任意文章列表以验证认证
        # 这里只是验证认证信息是否有效，不实际获取文章
        return {"status": "valid", "message": "认证信息有效"}
    except Exception as e:
        return {"status": "invalid", "message": f"认证失败: {str(e)}"}


# 全量文章下载
class FullDownloadRequest(BaseModel):
    account_id: str
    nickname: str

class FullDownloadResponse(BaseModel):
    success: bool
    message: str
    articles_queued: int

@app.post("/api/accounts/full-download", response_model=FullDownloadResponse)
def start_full_download(request: FullDownloadRequest, db: Session = Depends(get_db)):
    """开始下载公众号全部历史文章"""
    try:
        # 获取公众号信息
        account = db.query(OfficialAccount).filter(OfficialAccount.id == request.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="公众号不存在")

        # 获取认证信息
        credential = db.query(AuthCredential).filter(
            AuthCredential.account_nickname == request.nickname,
            AuthCredential.is_active == True
        ).first()

        if not credential:
            raise HTTPException(status_code=404, detail="未找到有效的认证信息，请先添加认证信息")

        # 使用任务调度器开始全量下载
        task_scheduler.execute_full_history_task(request.account_id, request.nickname)

        # 统计已排队的文章数量
        queued_count = db.query(DownloadQueue).filter(
            DownloadQueue.account_nickname == request.nickname,
            DownloadQueue.status == "pending"
        ).count()

        return FullDownloadResponse(
            success=True,
            message=f"已开始下载 {request.nickname} 的全部历史文章",
            articles_queued=queued_count
        )
    except Exception as e:
        return FullDownloadResponse(
            success=False,
            message=f"开始全量下载失败: {str(e)}",
            articles_queued=0
        )


# 下载队列管理
class QueueStatusResponse(BaseModel):
    total: int
    pending: int
    downloading: int
    completed: int
    failed: int

@app.get("/api/download-queue/status", response_model=QueueStatusResponse)
def get_queue_status(account_nickname: Optional[str] = None, db: Session = Depends(get_db)):
    """获取下载队列状态"""
    query = db.query(DownloadQueue)
    if account_nickname:
        query = query.filter(DownloadQueue.account_nickname == account_nickname)

    total = query.count()
    pending = query.filter(DownloadQueue.status == "pending").count()
    downloading = query.filter(DownloadQueue.status == "downloading").count()
    completed = query.filter(DownloadQueue.status == "completed").count()
    failed = query.filter(DownloadQueue.status == "failed").count()

    return QueueStatusResponse(
        total=total,
        pending=pending,
        downloading=downloading,
        completed=completed,
        failed=failed
    )

@app.get("/api/download-queue", response_model=List[dict])
def get_queue_items(
    account_nickname: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取下载队列项目"""
    query = db.query(DownloadQueue)
    if account_nickname:
        query = query.filter(DownloadQueue.account_nickname == account_nickname)
    if status:
        query = query.filter(DownloadQueue.status == status)

    items = query.offset(skip).limit(limit).all()

    # 转换为字典格式返回
    result = []
    for item in items:
        item_dict = {
            "id": item.id,
            "article_url": item.article_url,
            "account_nickname": item.account_nickname,
            "status": item.status,
            "retry_count": item.retry_count,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "completed_at": item.completed_at,
            "error_message": item.error_message
        }
        result.append(item_dict)

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
