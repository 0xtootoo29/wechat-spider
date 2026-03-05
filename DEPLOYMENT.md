# 微信公众号文章爬虫系统 - 服务器部署指南

## 部署前准备

### 服务器要求
- **最低配置**：2 核 CPU，2GB 内存
- **推荐配置**：2 核 CPU，4GB 内存
- **操作系统**：Linux (Ubuntu 20.04+ 或 CentOS 7+)
- **已安装软件**：
  - Docker (v20.0+)
  - Docker Compose (v2.0+)

### 系统资源预留
由于服务器同时运行 OpenClaw，爬虫系统配置为轻量化模式：
- 限制内存使用：1GB
- 限制 CPU 使用：80%
- 限制并发：1个工作进程

## 部署步骤

### 1. 克隆项目代码
```bash
# SSH 用户身份登录服务器
ssh username@your-server-ip

# 进入适当的目录
cd ~/apps  # 或你选择的目录

# 克隆项目
git clone https://github.com/yourusername/wechat-article-downloader.git
cd wechat-article-downloader
```

### 2. 构建 Docker 镜像
```bash
# 构建镜像（首次部署需要）
docker-compose build

# 或者直接使用预构建镜像（如果有）
# 修改 docker-compose.yml 中的 image 部分
```

### 3. 初始化数据库
```bash
# 启动服务
docker-compose up -d

# 初始化数据库表
docker exec -it wechat-article-downloader-pro python init_db.py

# 检查服务状态
docker-compose ps
```

### 4. 配置优化
系统已经针对 2G 内存服务器进行了优化配置，主要包括：
- 并发数限制：1 个 worker
- 批处理数量：5 篇文章
- 数据库连接池：3 个连接
- 请求间隔：最小 3 分钟

### 5. 配置认证信息
首次使用需要添加公众号认证信息：

1. 访问 `http://your-server-ip:8000`
2. 点击"认证管理" → "添加认证信息"
3. 输入公众号昵称、Cookie 和 Token
4. 获取方式：
   - 登录公众号后台 `mp.weixin.qq.com`
   - 打开浏览器开发者工具
   - 刷新页面，在 Network 标签中查找任意请求
   - 复制 Request Headers 中的 Cookie 和 Query String Parameters 中的 token

## 轻量化特性

### 1. 资源限制
- **内存限制**：1GB
- **CPU 限制**：80%
- **进程限制**：1 个 worker

### 2. 速率控制
- **请求间隔**：3-5 分钟
- **批量大小**：10 篇/批（原为 30）
- **批次暂停**：30 分钟

### 3. 数据库优化
- **连接池**：3 个连接
- **连接回收**：1 小时

## 监控和维护

### 1. 服务状态检查
```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f wechat-article-downloader

# 查看资源使用情况
docker stats wechat-article-downloader-pro
```

### 2. 日志管理
- 日志文件位置：`./logs/`
- 日志保留：7 天
- 日志轮转：自动

### 3. 数据备份
```bash
# 备份数据目录
tar -czf backup-$(date +%Y%m%d).tar.gz ./data/

# 定期备份脚本（添加到 crontab）
0 2 * * * cd /path/to/wechat-article-downloader && tar -czf backup-$(date +%Y%m%d).tar.gz ./data/
```

### 4. 定期维护
```bash
# 清理旧的 Docker 镜像
docker system prune -f

# 清理应用日志（超过7天的）
find ./logs -name "*.log" -mtime +7 -delete
```

## 启动和停止

### 启动服务
```bash
# 启动服务
docker-compose up -d

# 检查健康状态
curl http://localhost:8000/
```

### 停止服务
```bash
# 停止服务
docker-compose down

# 停止并删除容器
docker-compose down -v
```

### 重启服务
```bash
# 重启服务
docker-compose restart

# 或者重新部署
docker-compose down && docker-compose up -d
```

## 性能调优

### 环境变量调整
可以根据服务器负载调整以下环境变量（在 docker-compose.yml 中）：

- `MAX_WORKERS`: 工作进程数（默认：1）
- `BATCH_SIZE`: 批处理数量（默认：5）
- `CONCURRENT_DOWNLOADS`: 并发下载数（默认：1）
- `MIN_DELAY`: 请求最小间隔秒数（默认：180）

### 监控指标
系统提供以下监控指标：
- 数据库连接数
- 内存使用率
- 队列处理状态
- 任务执行状态

## 故障排除

### 1. 服务无法启动
```bash
# 检查日志
docker-compose logs

# 检查端口占用
netstat -tlnp | grep 8000

# 检查磁盘空间
df -h
```

### 2. 内存不足
- 确认 Docker 资源限制设置正确
- 检查其他服务资源使用情况
- 考虑增加服务器内存

### 3. 数据库连接问题
- 检查数据库文件权限
- 确认 SQLite 支持
- 检查磁盘空间

### 4. 认证失败
- 确认 Cookie 和 Token 仍然有效
- 检查公众号后台登录状态
- 重新获取认证信息

## 安全建议

1. **防火墙配置**：限制访问 IP
2. **定期更新**：保持系统和 Docker 镜像更新
3. **访问控制**：使用反向代理添加额外安全层
4. **认证信息保护**：定期更换 Cookie/Token

## OpenClaw 共存建议

由于服务器同时运行 OpenClaw，请注意：
- 监控总内存使用，确保两个服务都有足够资源
- 可以设置不同的运行时段避免资源竞争
- 定期检查系统负载