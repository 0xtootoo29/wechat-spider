"""
微信公众号爬虫系统 - 服务器优化配置

针对 2G RAM / 2核 CPU 服务器的轻量化配置
"""
import os

# 系统资源配置
SYSTEM_CONFIG = {
    "MAX_WORKERS": 2,  # 最大并发工作线程数
    "MEMORY_LIMIT_MB": 1024,  # 内存使用限制（MB）
    "BATCH_SIZE": 10,  # 每批处理的文章数量（原来是30，现在降低以节省内存）
    "CONCURRENT_DOWNLOADS": 2,  # 并发下载数
}

# 爬虫速率配置
CRAWLER_RATE_LIMIT = {
    "MIN_DELAY_BETWEEN_REQUESTS": 180,  # 最小延迟（秒）- 3分钟
    "MAX_DELAY_BETWEEN_REQUESTS": 300,  # 最大延迟（秒）- 5分钟
    "INITIAL_BACKOFF": 300,  # 初始退避时间（秒）
    "MAX_BACKOFF": 7200,  # 最大退避时间（秒）- 2小时
    "BACKOFF_FACTOR": 2,  # 退避倍数因子
    "BATCH_SIZE": 10,  # 每批处理数量（已从30降至10）
    "BATCH_PAUSE_DURATION": 1800,  # 批次间暂停时间（秒）- 30分钟
}

# 数据库优化配置
DATABASE_CONFIG = {
    "POOL_SIZE": 5,  # 连接池大小
    "MAX_OVERFLOW": 10,  # 最大溢出连接数
    "POOL_TIMEOUT": 30,  # 连接超时
    "POOL_RECYCLE": 3600,  # 连接回收时间（秒）
}

# 任务调度优化
TASK_SCHEDULER_CONFIG = {
    "CHECK_INTERVAL": 60,  # 任务检查间隔（秒）
    "MAX_TASK_RETRY": 3,  # 最大重试次数
    "CLEANUP_INTERVAL": 3600,  # 清理间隔（秒）- 1小时
}

# 文件处理优化
FILE_PROCESS_CONFIG = {
    "TEMP_DIR_MAX_SIZE": 512 * 1024 * 1024,  # 临时目录最大大小（512MB）
    "IMAGE_DOWNLOAD_TIMEOUT": 30,  # 图片下载超时（秒）
    "ARTICLE_SAVE_BATCH": 5,  # 文章批量保存数量
}

# 性能监控配置
MONITORING_CONFIG = {
    "ENABLE_METRICS": True,  # 启用指标收集
    "METRICS_INTERVAL": 300,  # 指标收集间隔（秒）- 5分钟
    "MEMORY_CHECK_INTERVAL": 60,  # 内存检查间隔（秒）
    "ALERT_THRESHOLD": 80,  # 内存使用警报阈值（%）
}

# 日志配置
LOGGING_CONFIG = {
    "LEVEL": "INFO",  # 日志级别
    "RETENTION_DAYS": 7,  # 日志保留天数
    "MAX_FILE_SIZE": 10 * 1024 * 1024,  # 单个日志文件最大大小（10MB）
}

# API 限流配置
API_RATE_LIMIT = {
    "REQUESTS_PER_MINUTE": 60,  # 每分钟请求数限制
    "BURST_LIMIT": 10,  # 突发请求数限制
}

def get_optimized_config():
    """获取针对低配服务器的优化配置"""
    return {
        "system": SYSTEM_CONFIG,
        "crawler": CRAWLER_RATE_LIMIT,
        "database": DATABASE_CONFIG,
        "scheduler": TASK_SCHEDULER_CONFIG,
        "file_process": FILE_PROCESS_CONFIG,
        "monitoring": MONITORING_CONFIG,
        "logging": LOGGING_CONFIG,
        "api_rate_limit": API_RATE_LIMIT,
    }

# 环境变量覆盖
def load_config_from_env():
    """从环境变量加载配置以允许运行时调整"""
    config = get_optimized_config()

    # 系统资源
    SYSTEM_CONFIG["MAX_WORKERS"] = int(os.getenv("MAX_WORKERS", SYSTEM_CONFIG["MAX_WORKERS"]))
    SYSTEM_CONFIG["BATCH_SIZE"] = int(os.getenv("BATCH_SIZE", SYSTEM_CONFIG["BATCH_SIZE"]))
    SYSTEM_CONFIG["CONCURRENT_DOWNLOADS"] = int(os.getenv("CONCURRENT_DOWNLOADS", SYSTEM_CONFIG["CONCURRENT_DOWNLOADS"]))

    # 爬虫速率
    CRAWLER_RATE_LIMIT["MIN_DELAY_BETWEEN_REQUESTS"] = int(os.getenv("MIN_DELAY", CRAWLER_RATE_LIMIT["MIN_DELAY_BETWEEN_REQUESTS"]))
    CRAWLER_RATE_LIMIT["BATCH_SIZE"] = int(os.getenv("CRAWLER_BATCH_SIZE", CRAWLER_RATE_LIMIT["BATCH_SIZE"]))

    # 数据库
    DATABASE_CONFIG["POOL_SIZE"] = int(os.getenv("DB_POOL_SIZE", DATABASE_CONFIG["POOL_SIZE"]))

    return config