# WeChat Article Downloader 📥

微信公众号历史文章下载工具

## ✨ 功能特性

### Phase 1 ✅ - 基础框架
- [x] 公众号管理（添加、编辑、删除）
- [x] 公众号抓取测试（连通性、ID验证、文章抓取）
- [x] Web 管理界面

### Phase 2 ✅ - 任务调度
- [x] 定时任务系统（每小时/每天/每周）
- [x] 自动抓取文章
- [x] Markdown 格式存储
- [x] 执行日志记录

### Phase 3 ✅ - AI 智能分析
- [x] 文章内容摘要
- [x] 关键词提取
- [x] 自动分类（科技/财经/教育/健康/娱乐/生活/时政）
- [x] 情感分析（正面/中性/负面）
- [x] 分析报告生成

### Phase 4 ✅ - 前端优化
- [x] 响应式界面设计
- [x] 任务管理卡片
- [x] 文章列表展示
- [x] 数据可视化

## 🚀 快速开始

### 1. 安装依赖
```bash
cd wechat-article-downloader
pip install -r requirements.txt --break-system-packages
```

### 2. 启动服务
```bash
cd app
python main.py
```

### 3. 访问应用
打开浏览器访问: http://localhost:8000

## 🧪 运行测试
```bash
python test_app.py
```

## 📁 项目结构
```
wechat-article-downloader/
├── app/
│   ├── main.py              # FastAPI 主应用
│   ├── models.py            # 数据库模型
│   ├── spider/              # 抓取引擎
│   │   └── wechat_spider.py
│   ├── scheduler/           # 任务调度
│   │   └── task_scheduler.py
│   ├── ai/                  # AI 分析
│   │   └── analyzer.py
│   ├── templates/           # HTML 模板
│   │   └── dashboard.html
│   └── static/              # 静态文件
│       └── css/
├── data/                    # 数据存储
│   └── articles/           # 抓取的文章
├── logs/                    # 日志文件
├── test_app.py             # 测试脚本
├── requirements.txt
└── README.md
```

## 🔧 核心功能

### 公众号管理
- 添加公众号（支持测试功能）
- 公众号分组管理
- 抓取连通性测试

### 任务调度
- 定时抓取（每小时/每天/每周）
- 手动触发任务
- 任务执行日志

### 文章存储
- Markdown 格式保存
- 自动分类归档
- 原文链接保留

### AI 分析
- 智能摘要生成
- 关键词提取
- 情感倾向分析
- 文章分类
- 数据报告

## 📊 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **调度**: APScheduler
- **前端**: Bootstrap 5 + JavaScript
- **抓取**: BeautifulSoup + requests
- **AI**: 本地智能分析（无需外部 API）

## 📝 使用流程

1. **添加公众号** → 输入微信号 → 测试抓取
2. **创建任务** → 选择公众号 → 设置抓取周期
3. **自动抓取** → 定时运行 → 保存文章
4. **AI 分析** → 自动分析 → 生成报告
5. **查看文章** → 浏览列表 → 查看详情

## ⚠️ 注意事项

- 抓取频率不宜过高，建议每天1-2次
- 部分公众号可能需要等待搜狗收录
- 请遵守相关网站的使用条款

## 🔗 相关链接

- **代码仓库**: https://github.com/0xtootoo29/wechat-article-downloader
- **问题反馈**: 在 GitHub Issues 提交

## 📄 License

MIT License

---

**开发完成！** 🎉 所有功能已就绪，可以开始使用。
