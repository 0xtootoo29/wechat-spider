# WeChat Spider Pro

微信公众号自动抓取与分析工具

## 功能特性

- ✅ 公众号管理（添加、编辑、删除、测试）
- ✅ 任务调度（定时抓取、周期配置）
- ✅ 文章存储（Markdown 格式）
- ✅ AI 智能分析（摘要、关键词、情感分析）
- ✅ Web 管理界面

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
cd app
python main.py

# 访问 http://localhost:8000
```

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **前端**: Bootstrap 5 + JavaScript
- **抓取引擎**: BeautifulSoup + requests
- **AI 分析**: Claude API

## 项目结构

```
wechat-spider/
├── app/
│   ├── main.py           # FastAPI 主应用
│   ├── models.py         # 数据库模型
│   ├── spider/           # 抓取引擎
│   ├── templates/        # HTML 模板
│   └── static/           # 静态文件
├── data/                 # 数据存储
├── logs/                 # 日志文件
└── requirements.txt      # 依赖
```

## 开发计划

- [x] Phase 1: 基础框架
- [x] Phase 2: 公众号管理 + 测试功能
- [ ] Phase 3: 任务系统 + 抓取引擎
- [ ] Phase 4: AI 分析模块
- [ ] Phase 5: 前端优化

## License

MIT
