"""
TextNow 客服系统 - 集中配置
所有敏感信息和可配置参数统一从这里管理。
生产环境请通过环境变量覆盖，不要修改此文件中的明文密码。
"""

import os

# ===================== 数据库 =====================
# 优先级：环境变量 > 本文件默认值
DB_HOST = os.getenv("TN_DB_HOST", "170.106.106.252")
DB_PORT = int(os.getenv("TN_DB_PORT", "13306"))
DB_USER = os.getenv("TN_DB_USER", "root")
DB_PASS = os.getenv("TN_DB_PASS", "Ws961230&@^%#&!")
DB_NAME = os.getenv("TN_DB_NAME", "textnow")

# ===================== SOCKS5 代理 =====================
# 使用 socks5h:// 而非 socks5://，让代理端做 DNS 解析，避免 DNS 泄露和连接问题
PROXY_RAW = os.getenv(
    "TN_PROXY",
    "socks5h://ns-nscart01_area-US_session-s2vgbEpOHl_life-10:miller1213@rotate.isp.nsocks.com:6121"
)
PROXY = {"http": PROXY_RAW, "https": PROXY_RAW}

# ===================== 客服服务配置 =====================
POLL_INTERVAL = int(os.getenv("TN_POLL_INTERVAL", "15"))       # 轮询间隔（秒）
AUTO_REPLY_ENABLED = os.getenv("TN_AUTO_REPLY", "1") == "1"
MAX_WORKERS = int(os.getenv("TN_MAX_WORKERS", "4"))             # 并发处理账号数

# ===================== Web 控制台配置 =====================
WEB_HOST = os.getenv("TN_WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("TN_WEB_PORT", "8899"))
WEB_USER = os.getenv("TN_WEB_USER", "admin")                    # 控制台登录用户名
WEB_PASS = os.getenv("TN_WEB_PASS", "admin123")                 # 控制台登录密码（生产环境请修改！）

# ===================== 注册配置 =====================
REGISTER_SLEEP_MIN = int(os.getenv("TN_REG_SLEEP_MIN", "60"))
REGISTER_SLEEP_MAX = int(os.getenv("TN_REG_SLEEP_MAX", "120"))
REGISTER_PASSWORD = os.getenv("TN_REG_PASSWORD", "Abc123456")

# ===================== 日志 =====================
LOG_LEVEL = os.getenv("TN_LOG_LEVEL", "INFO")
