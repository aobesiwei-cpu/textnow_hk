"""
TextNow 客服系统 - 共享数据库模块
使用 DBUtils 连接池，避免频繁建连；统一 charset=utf8mb4。
"""

import pymysql
import logging
from dbutils.pooled_db import PooledDB

from tn_config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

log = logging.getLogger(__name__)

# 全局连接池（懒初始化）
_pool = None


def init_pool():
    """初始化连接池，应在程序启动时调用一次。"""
    global _pool
    if _pool is not None:
        return _pool
    _pool = PooledDB(
        creator=pymysql,
        maxconnections=20,      # 最大连接数
        mincached=2,            # 初始化时建立的空闲连接数
        maxcached=5,            # 最大空闲连接数
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        connect_timeout=10,
        ping=1,                 # 每次取连接时 ping 一次，自动重连
        ssl_disabled=True,      # 禁用 SSL（本地调试）
    )
    log.info("✅ 数据库连接池初始化完成 (host=%s, db=%s)", DB_HOST, DB_NAME)
    return _pool


def get_db():
    """从连接池取一个连接。用完无需手动 close()，交给 with 或调用者。"""
    if _pool is None:
        init_pool()
    return _pool.connection()


def get_db_dict():
    """返回带 DictCursor 的连接（字段名访问）。"""
    conn = get_db()
    # pymysql 的 DictCursor 需要通过 cursor 指定，不能直接传给 connect()
    # 所以这里返回一个普通连接，使用时 cur = conn.cursor(pymysql.cursors.DictCursor)
    return conn


# ===================== Schema 初始化 =====================
def init_schema():
    """
    幂等建表。只在表不存在时创建，不修改已有表结构。
    如需变更表结构，请手写 ALTER SQL 或在单独迁移脚本中处理。
    """
    conn = get_db()
    cur = conn.cursor()

    # conversations 表
    cur.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        account_id INT NOT NULL,
        contact_number VARCHAR(32) NOT NULL,
        contact_username VARCHAR(64),
        status TINYINT DEFAULT 1,
        last_message_time DATETIME,
        agent_id VARCHAR(64),
        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_account_contact (account_id, contact_number),
        INDEX idx_status (status),
        INDEX idx_last_time (last_message_time),
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")

    # messages 表
    cur.execute("""CREATE TABLE IF NOT EXISTS messages (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        conversation_id INT NOT NULL,
        direction TINYINT NOT NULL,
        content TEXT NOT NULL,
        message_type TINYINT DEFAULT 1,
        is_auto_reply TINYINT DEFAULT 0,
        sent_time DATETIME NOT NULL,
        read_status TINYINT DEFAULT 0,
        raw_data TEXT,
        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_conversation (conversation_id, sent_time),
        INDEX idx_direction (direction),
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")

    # reply_templates 表
    cur.execute("""CREATE TABLE IF NOT EXISTS reply_templates (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(64) NOT NULL,
        shortcut VARCHAR(32) NOT NULL,
        content TEXT NOT NULL,
        category VARCHAR(32),
        is_active TINYINT DEFAULT 1,
        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_shortcut (shortcut)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")

    # cs_settings 表
    cur.execute("""CREATE TABLE IF NOT EXISTS cs_settings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        `key` VARCHAR(64) NOT NULL UNIQUE,
        `value` TEXT,
        updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")

    conn.commit()

    # 插入默认模板（IGNORE 避免重复）
    defaults = [
        ('欢迎语', '/welcome', '您好！感谢联系我们，请问有什么可以帮您？', 'greeting'),
        ('价格咨询', '/price', '我们的服务价格如下：\n基础版：$9.99/月\n高级版：$19.99/月\n如有疑问请随时告诉我！', 'price'),
        ('技术支持', '/support', '请描述您遇到的问题，我们的技术团队会尽快回复您。', 'support'),
        ('结束语', '/close', '感谢您的咨询，祝您生活愉快！如有需要请随时联系我们。', 'close'),
        ('自动回复', '/auto', '您好，我已收到您的消息，稍后会尽快回复您。', 'auto'),
    ]
    for name, shortcut, content, category in defaults:
        cur.execute(
            "INSERT IGNORE INTO reply_templates (name, shortcut, content, category) VALUES (%s,%s,%s,%s)",
            (name, shortcut, content, category)
        )

    # 插入默认配置
    defaults_settings = [
        ('auto_reply_enabled', '1'),
        ('auto_reply_template', '/auto'),
        ('poll_interval', '15'),
        ('max_concurrent_chats', '5'),
        ('work_start_hour', '9'),
        ('work_end_hour', '21'),
    ]
    for key, val in defaults_settings:
        cur.execute(
            "INSERT IGNORE INTO cs_settings (`key`, `value`) VALUES (%s,%s)",
            (key, val)
        )

    conn.commit()
    conn.close()
    log.info("✅ 客服系统数据表初始化完成（含默认数据）")


def init_accounts_schema():
    """
    初始化 accounts 表（供注册脚本使用）。
    确保 charset=utf8mb4 在整个连接链路上一致。
    """
    import pymysql as _pymysql
    # 先连 MySQL 不指定数据库，建库再连库
    conn = _pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        charset="utf8mb4",
        connect_timeout=10,
        ssl_disabled=True
    )
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.select_db(DB_NAME)
    cur.execute("""CREATE TABLE IF NOT EXISTS accounts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cookie TEXT,
        idfa VARCHAR(64),
        user_agent TEXT,
        px_auth TEXT,
        device_fp VARCHAR(64),
        os_version VARCHAR(20),
        client_id VARCHAR(128),
        email VARCHAR(128),
        phone VARCHAR(32),
        username VARCHAR(64),
        status TINYINT DEFAULT 1,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    conn.commit()
    conn.close()
    log.info("✅ accounts 表初始化完成")
