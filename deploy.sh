#!/bin/bash
# 一键部署脚本 - 在服务器上运行

echo "🚀 WeChat Article Downloader 一键部署脚本"
echo "===================================="

# 检查是否安装了 git
if ! command -v git &> /dev/null; then
    echo "❌ 请先安装 git"
    exit 1
fi

# 检查是否安装了 docker
if ! command -v docker &> /dev/null; then
    echo "📦 正在安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✅ Docker 安装完成，请重新登录后再次运行此脚本"
    exit 0
fi

# 克隆代码
echo "📥 正在下载代码..."
if [ -d "wechat-article-downloader" ]; then
    cd wechat-article-downloader
    git pull
else
    git clone https://github.com/daviddeng1980/wechat-article-downloader.git
    cd wechat-article-downloader
fi

# 使用 Docker Compose 启动
echo "🐳 正在启动服务..."
docker-compose up -d --build

# 检查状态
echo "🔍 检查服务状态..."
sleep 5
if docker ps | grep -q wechat-article-downloader; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "🌐 访问地址:"
    echo "   本地: http://localhost:8000"
    echo "   公网: http://$(curl -s ifconfig.me):8000"
    echo ""
    echo "📊 查看日志:"
    echo "   docker logs -f wechat-article-downloader"
    echo ""
    echo "🛑 停止服务:"
    echo "   docker-compose down"
else
    echo "❌ 服务启动失败，请检查日志:"
    echo "   docker logs wechat-article-downloader"
fi
