from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_id():
    return str(uuid.uuid4())[:8]

# 公众号模型
class OfficialAccount(Base):
    __tablename__ = "official_accounts"
    
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False)  # 公众号名称
    wechat_id = Column(String, nullable=False, unique=True)  # 微信号
    gh_id = Column(String, nullable=True)  # gh_xxx ID
    description = Column(Text, nullable=True)  # 描述
    category = Column(String, nullable=True)  # 分类
    status = Column(Boolean, default=True)  # 状态
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    tasks = relationship("Task", back_populates="account")
    articles = relationship("Article", back_populates="account")

# 公众号组模型
class AccountGroup(Base):
    __tablename__ = "account_groups"
    
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False)  # 组名
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

# 组和公众号关联表
class GroupMember(Base):
    __tablename__ = "group_members"
    
    id = Column(String, primary_key=True, default=generate_id)
    group_id = Column(String, ForeignKey("account_groups.id"))
    account_id = Column(String, ForeignKey("official_accounts.id"))

# 任务模型
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False)  # 任务名称
    account_id = Column(String, ForeignKey("official_accounts.id"), nullable=True)
    group_id = Column(String, ForeignKey("account_groups.id"), nullable=True)
    
    # 调度配置
    schedule_type = Column(String, default="daily")  # realtime/hourly/daily/weekly
    schedule_time = Column(String, default="08:00")  # 执行时间
    fetch_depth = Column(Integer, default=10)  # 抓取深度（最近N篇）
    fetch_days = Column(Integer, default=7)  # 抓取天数
    storage_format = Column(String, default="markdown")  # markdown/json/html
    storage_path = Column(String, default="./data/articles")  # 存储路径
    ai_analysis = Column(Boolean, default=True)  # 是否开启AI分析
    
    # 状态
    status = Column(String, default="active")  # active/paused/stopped
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联
    account = relationship("OfficialAccount", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task")

# 任务执行日志
class TaskLog(Base):
    __tablename__ = "task_logs"
    
    id = Column(String, primary_key=True, default=generate_id)
    task_id = Column(String, ForeignKey("tasks.id"))
    status = Column(String, default="running")  # running/success/failed
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    articles_count = Column(Integer, default=0)
    error_msg = Column(Text, nullable=True)
    
    task = relationship("Task", back_populates="logs")

# 文章模型
class Article(Base):
    __tablename__ = "articles"
    
    id = Column(String, primary_key=True, default=generate_id)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    publish_time = Column(DateTime, nullable=True)
    fetch_time = Column(DateTime, default=datetime.now)
    
    # 关联
    account_id = Column(String, ForeignKey("official_accounts.id"))
    task_id = Column(String, ForeignKey("tasks.id"))
    
    # AI分析结果
    ai_summary = Column(Text, nullable=True)
    keywords = Column(String, nullable=True)  # JSON格式存储
    sentiment = Column(String, nullable=True)  # positive/neutral/negative
    category = Column(String, nullable=True)
    
    # 文件存储
    file_path = Column(String, nullable=True)
    
    account = relationship("OfficialAccount", back_populates="articles")

# 数据库初始化
engine = create_engine("sqlite:///./data/wechat_spider.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
