# WeChat Spider Pro - Windows 部署脚本
# 保存为 deploy.ps1 在服务器上运行

# 1. 安装 Python
Write-Host "检查 Python..." -ForegroundColor Green
$pythonPath = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    Write-Host "正在下载 Python..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" -OutFile "C:\Temp\python-installer.exe"
    Start-Process -FilePath "C:\Temp\python-installer.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    Write-Host "Python 安装完成，请重启 PowerShell 后重新运行此脚本" -ForegroundColor Red
    exit
}

# 2. 创建目录
$appDir = "C:\WeChatSpider"
New-Item -ItemType Directory -Force -Path $appDir
Set-Location $appDir

# 3. 克隆代码（或复制本地代码）
Write-Host "部署应用..." -ForegroundColor Green
# 这里需要手动复制代码到 $appDir

# 4. 安装依赖
Write-Host "安装依赖..." -ForegroundColor Green
pip install -r requirements.txt

# 5. 创建 Windows 服务
Write-Host "创建 Windows 服务..." -ForegroundColor Green
$serviceName = "WeChatSpider"
$pythonPath = (Get-Command python).Source
$scriptPath = "$appDir\app\main.py"

# 使用 nssm 创建服务
if (-not (Test-Path "C:\nssm\nssm.exe")) {
    Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "C:\Temp\nssm.zip"
    Expand-Archive -Path "C:\Temp\nssm.zip" -DestinationPath "C:\nssm"
}

C:\nssm\nssm.exe install $serviceName $pythonPath $scriptPath
C:\nssm\nssm.exe set $serviceName DisplayName "WeChat Spider Pro"
C:\nssm\nssm.exe set $serviceName Description "微信公众号自动抓取服务"
C:\nssm\nssm.exe set $serviceName Start SERVICE_AUTO_START

# 6. 启动服务
Start-Service $serviceName
Write-Host "服务已启动！" -ForegroundColor Green
Write-Host "访问地址: http://localhost:8000" -ForegroundColor Cyan

# 7. 配置防火墙
Write-Host "配置防火墙..." -ForegroundColor Green
New-NetFirewallRule -DisplayName "WeChatSpider" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow

Write-Host "部署完成！" -ForegroundColor Green
Write-Host "公网访问: http://你的服务器IP:8000" -ForegroundColor Yellow
