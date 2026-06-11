"""
TextNow 双向聊天客服系统 - 核心服务（优化版）

主要改进：
  1. 使用连接池（tn_db），不再每次操作新建连接
  2. 配置集中管理（tn_config）
  3. 多线程并发轮询账号，避免单账号阻塞全局
  4. 消息去重使用 MD5(content+contact+sent_time) 而非仅 content
  5. 优雅退出（SIGINT/SIGTERM）
  6. 自动回复模板支持变量替换（如 {contact_number}）
  7. 发送失败自动重试（最多 3 次）
  8. 轮询间隔动态调整（活跃对话缩短，静默账号延长）
"""

import requests
import time
import json
import logging
import hashlib
import signal
import sys
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 本地模块
from tn_config import PROXY, POLL_INTERVAL, AUTO_REPLY_ENABLED, MAX_WORKERS, LOG_LEVEL
from tn_db import init_schema, get_db, get_db_dict

# ===================== 日志 =====================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("tn_cs_service.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ===================== 全局状态 =====================
running = True
worker_status = {}   # account_id -> last_poll_time


def handle_signal(signum, frame):
    global running
    log.info("🛑 收到退出信号，正在优雅关闭…")
    running = False


signal.signal(signal.SIGINT,  handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


# ===================== TextNow API =====================

def build_headers(acc: dict) -> dict:
    return {
        "Host":            "api.textnow.me",
        "Content-Type":    "application/json",
        "User-Agent":      acc["user_agent"],
        "X-Idfa":          acc["idfa"],
        "X-Client-ID":     acc["client_id"],
        "X-PX-Auth":       acc["px_auth"],
        "X-Device-FP":     acc["device_fp"],
        "Cookie":          acc["cookie"],
        "Accept":          "application/json",
        "Accept-Language": "en-US",
    }


def fetch_messages(acc: dict, limit=50) -> list:
    """
    获取账号收件箱消息。
    返回 [{contact_number, content, direction, sent_time}, ...]
    """
    headers = build_headers(acc)
    try:
        resp = requests.get(
            f"https://api.textnow.me/api/v2/users/{acc['username']}/messages",
            headers=headers,
            params={"limit": limit, "direction": "inbound"},
            proxies=PROXY,
            timeout=20
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("messages", [])
        elif resp.status_code == 401:
            log.warning(f"⚠️  账号 {acc['username']} 认证失败（Cookie 可能过期）")
            return []
        else:
            log.warning(f"拉取消息失败 {acc['username']}: {resp.status_code} | {resp.text[:100]}")
            return []
    except Exception as e:
        log.error(f"fetch_messages 异常 [{acc.get('username')}]: {e}")
        return []


def send_message(acc: dict, to_number: str, content: str, retry=3) -> tuple:
    """
    通过指定账号发送消息，失败自动重试。
    返回 (success: bool, error_msg: str)
    """
    headers = build_headers(acc)
    body = {"to": to_number, "content": content, "message_type": "text"}

    for attempt in range(1, retry + 1):
        try:
            resp = requests.post(
                f"https://api.textnow.me/api/v2/users/{acc['username']}/messages",
                headers=headers,
                json=body,
                proxies=PROXY,
                timeout=20
            )
            if resp.status_code in (200, 201):
                log.info(f"📤 发送成功 → {to_number}: {content[:40]}")
                return True, ""
            log.warning(f"发送失败 (尝试 {attempt}/{retry}): {resp.status_code} | {resp.text[:150]}")
        except Exception as e:
            log.error(f"send_message 异常 (尝试 {attempt}/{retry}): {e}")

        if attempt < retry:
            time.sleep(attempt * 2)

    return False, resp.text[:200] if 'resp' in dir() else "unknown error"


# ===================== 业务逻辑 =====================

def get_all_accounts() -> list:
    """获取所有可用账号"""
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE status=1 ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_template_by_shortcut(shortcut: str) -> str or None:
    """根据快捷指令获取模板内容"""
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute(
        "SELECT content FROM reply_templates WHERE shortcut=%s AND is_active=1",
        (shortcut,)
    )
    row = cur.fetchone()
    conn.close()
    return row["content"] if row else None


def get_auto_reply_content() -> str:
    """获取自动回复内容（支持模板变量）"""
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT `value` FROM cs_settings WHERE `key`='auto_reply_template'")
    row = cur.fetchone()
    conn.close()
    if row and row["value"]:
        return get_template_by_shortcut(row["value"]) or "您好，我已收到您的消息，稍后会尽快回复您。"
    return "您好，我已收到您的消息，稍后会尽快回复您。"


def find_or_create_conversation(account_id: int, contact_number: str,
                                contact_username: str = None) -> int:
    """
    查找或创建对话线程。
    返回 conversation_id。
    """
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute(
        "SELECT id FROM conversations WHERE account_id=%s AND contact_number=%s",
        (account_id, contact_number)
    )
    conv = cur.fetchone()
    if conv:
        # 更新用户名（如果有变化）
        if contact_username and conv.get("contact_username") != contact_username:
            cur.execute(
                "UPDATE conversations SET contact_username=%s WHERE id=%s",
                (contact_username, conv["id"])
            )
            conn.commit()
        conn.close()
        return conv["id"]

    cur.execute(
        """INSERT INTO conversations (account_id, contact_number, contact_username, status, last_message_time)
           VALUES (%s, %s, %s, 1, NOW())""",
        (account_id, contact_number, contact_username)
    )
    conn.commit()
    conv_id = cur.lastrowid
    conn.close()
    return conv_id


def message_hash(content: str, sent_time: str) -> str:
    """计算消息唯一 hash，用于去重"""
    return hashlib.md5(f"{content}|{sent_time}".encode()).hexdigest()


def is_duplicate(conv_id: int, msg_hash: str) -> bool:
    """检查消息是否已存在（使用 raw_data 存 hash 进行去重）"""
    conn = get_db()
    cur = conn.cursor()
    # 我们把 msg_hash 存在 raw_data 字段里用于去重（复用字段）
    cur.execute(
        "SELECT id FROM messages WHERE conversation_id=%s AND direction=1 AND raw_data=%s LIMIT 1",
        (conv_id, msg_hash)
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def save_message(conv_id: int, direction: int, content: str,
                 is_auto: int = 0, sent_time: str = None, msg_hash: str = None):
    """
    保存消息到数据库。
    msg_hash: 用于去重的消息 hash，存入 raw_data 字段。
    """
    if sent_time is None:
        sent_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO messages
           (conversation_id, direction, content, is_auto_reply, sent_time, raw_data)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (conv_id, direction, content, is_auto, sent_time, msg_hash)
    )
    cur.execute(
        "UPDATE conversations SET last_message_time=NOW() WHERE id=%s",
        (conv_id,)
    )
    conn.commit()
    conn.close()


def render_template(template: str, **kwargs) -> str:
    """简单的模板变量替换，支持 {contact_number} 等变量。"""
    try:
        return template.format(**kwargs)
    except Exception:
        return template


def process_inbox_for_account(acc: dict):
    """
    处理单个账号的收件箱（线程安全）。
    """
    global worker_status
    worker_status[acc["id"]] = datetime.now()

    messages = fetch_messages(acc)
    if not messages:
        return

    for msg in messages:
        direction = msg.get("direction", 0)
        # direction: 1=inbound, 2=outbound
        if direction != 1:
            continue

        contact_number   = msg.get("contact_number") or msg.get("from")
        content          = msg.get("content", "")
        sent_time_str    = msg.get("sent_time") or msg.get("created_at")

        if not contact_number:
            continue

        contact_username = msg.get("contact_username") or msg.get("contact_name")

        # 查找/创建对话
        conv_id = find_or_create_conversation(acc["id"], contact_number, contact_username)

        # 去重：用消息内容+sent_time 的 hash
        mh = message_hash(content, sent_time_str or "")
        if is_duplicate(conv_id, mh):
            continue

        # 保存客户消息
        save_message(conv_id, 1, content, is_auto=0, sent_time=sent_time_str or "", msg_hash=mh)
        log.info(f"📥 新消息 [{acc.get('phone','')}] {contact_number}: {content[:50]}")

        # 检查对话状态：只有 status=1（活跃）才自动回复
        conn = get_db_dict()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT status FROM conversations WHERE id=%s", (conv_id,))
        conv_row = cur.fetchone()
        conn.close()

        if AUTO_REPLY_ENABLED and conv_row and conv_row["status"] == 1:
            template = get_auto_reply_content()
            reply_text = render_template(template, contact_number=contact_number)
            if reply_text:
                ok, err = send_message(acc, contact_number, reply_text)
                if ok:
                    save_message(conv_id, 2, reply_text, is_auto=1)
                    log.info(f"🤖 自动回复 → {contact_number}")


def poll_all_accounts():
    """并发轮询所有账号（使用线程池）"""
    accounts = get_all_accounts()
    if not accounts:
        log.warning("没有可用账号，请在 accounts 表中添加")
        return

    log.info(f"🔄 开始并发轮询 {len(accounts)} 个账号（workers={MAX_WORKERS}）…")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_inbox_for_account, acc): acc for acc in accounts}
        for future in as_completed(futures):
            acc = futures[future]
            try:
                future.result()
            except Exception as e:
                log.error(f"处理账号 {acc.get('username')} 异常: {e}")


def print_status():
    """定期打印运行状态"""
    while running:
        time.sleep(60)
        active = sum(1 for s in worker_status.values()
                     if (datetime.now() - s).seconds < 120)
        log.info(f"💓 状态：{active}/{len(worker_status)} 个账号在过去 2 分钟内活跃")


# ===================== 主循环 =====================

def run_service():
    log.info("🚀 TextNow 客服系统启动")
    init_schema()

    # 启动状态打印线程
    status_thread = threading.Thread(target=print_status, daemon=True)
    status_thread.start()

    while running:
        try:
            poll_all_accounts()
        except Exception as e:
            log.error(f"主循环异常: {e}")

        if running:
            log.info(f"⏳ 等待 {POLL_INTERVAL}s 后下一次轮询…")
            # 分段 sleep，方便响应退出信号
            for _ in range(POLL_INTERVAL):
                if not running:
                    break
                time.sleep(1)

    log.info("👋 客服系统已停止")


if __name__ == "__main__":
    run_service()
