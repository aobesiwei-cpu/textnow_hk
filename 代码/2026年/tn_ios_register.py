"""
TextNow iOS 账号注册脚本（优化版）
修复：
  - 数据库连接编码问题（显式 charset=utf8mb4）
  - 代理协议使用 socks5h://（远程 DNS 解析）
  - 配置集中管理
  - 日志编码问题
  - 注册失败时的指数退避重试
"""

import requests
import uuid
import random
import string
import time
import json
import logging
import hmac
import hashlib
import base64

# 本地模块
from tn_config import (
    PROXY, REGISTER_SLEEP_MIN, REGISTER_SLEEP_MAX,
    REGISTER_PASSWORD, LOG_LEVEL
)
from tn_db import init_accounts_schema, get_db

# ===================== 日志 =====================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("tn_run.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ===================== 设备模板 =====================
DEVICE_TEMPLATES = [
    {"model": "iPhone14,7", "name": "iPhone 14",      "os_version": "16.1",  "scale": "3.00"},
    {"model": "iPhone12,1", "name": "iPhone 11",      "os_version": "16.3.1","scale": "2.00"},
    {"model": "iPhone13,2", "name": "iPhone 12",      "os_version": "16.5",  "scale": "3.00"},
    {"model": "iPhone14,5", "name": "iPhone 13",      "os_version": "16.0.2","scale": "3.00"},
    {"model": "iPhone15,2", "name": "iPhone 14 Pro",  "os_version": "17.0",  "scale": "3.00"},
    {"model": "iPhone15,4", "name": "iPhone 15",      "os_version": "17.1",  "scale": "3.00"},
]


def generate_idfa():
    return str(uuid.uuid4()).upper()


def generate_client_id():
    hex_part = ''.join(random.choice(string.hexdigits.lower()) for _ in range(32))
    num_part = ''.join(random.choice(string.digits) for _ in range(10))
    return f"{hex_part}x{num_part}"


def generate_random_email():
    first_names = ["Englebrecht", "Mcquilliams", "Schoepf", "Kesey", "Langford", "Wasserman"]
    last_names  = ["Lomuscio", "Swieand", "Ewert", "Kilian", "Hennessey", "Brigham"]
    num = random.randint(10, 9999)
    return f"{random.choice(first_names)}{random.choice(last_names)}{num}@outlook.com"


def generate_device_info():
    dev = random.choice(DEVICE_TEMPLATES)
    return {
        "idfa":       generate_idfa(),
        "device_fp":  generate_idfa(),
        "px_uuid":    str(uuid.uuid4()).upper(),
        "px_vid":     str(uuid.uuid4()).upper(),
        "device_model": dev["name"],
        "os_version":   dev["os_version"],
        "user_agent":   f'TextNow/26.1.0 ({dev["model"]}; iOS {dev["os_version"]}; Scale/{dev["scale"]})'
    }


def generate_px_auth(dev_info, ts):
    """生成 X-PX-Auth 头（反向工程自 TextNow iOS 客户端）"""
    secret = b"textnow_px_secret"
    raw = f'{dev_info["idfa"]}{dev_info["px_uuid"]}{ts}'.encode()
    sig = base64.b64encode(hmac.new(secret, raw, hashlib.sha256).digest()).decode()
    r64  = ''.join(random.choice(string.hexdigits.lower()) for _ in range(64))
    pad  = ''.join(random.choice(string.ascii_letters + string.digits + "+/=") for _ in range(200))
    return f"3:{r64}:{sig}:{pad}"


def build_headers(dev_info, client_id, px_auth):
    """构造 TextNow API 请求头"""
    return {
        "Host":            "api.textnow.me",
        "Content-Type":    "application/json",
        "User-Agent":      dev_info["user_agent"],
        "X-Idfa":          dev_info["idfa"],
        "X-Client-ID":     client_id,
        "X-PX-Auth":       px_auth,
        "X-Device-FP":     dev_info["device_fp"],
        "Accept":          "application/json",
        "Accept-Language": "en-US",
    }


def reg_one(max_retry=3):
    """
    注册一个账号，失败自动重试。
    返回账号 dict 或 None。
    """
    for attempt in range(1, max_retry + 1):
        dev      = generate_device_info()
        ts       = str(int(time.time() * 1000))
        email    = generate_random_email()
        client_id = generate_client_id()
        px_auth  = generate_px_auth(dev, ts)

        headers = build_headers(dev, client_id, px_auth)
        body = {
            "email":    email,
            "password": REGISTER_PASSWORD,
            "first_name": "User",
            "last_name":  "Test",
            "device": {
                "model":      dev["device_model"],
                "os_version": dev["os_version"],
                "idfa":       dev["idfa"]
            }
        }

        try:
            resp = requests.post(
                "https://api.textnow.me/api/v2/users",
                headers=headers,
                json=body,
                proxies=PROXY,
                timeout=25
            )
            if resp.status_code == 200:
                js  = resp.json()
                acc = {
                    "cookie":      resp.headers.get("Set-Cookie", ""),
                    "idfa":        dev["idfa"],
                    "user_agent":  dev["user_agent"],
                    "px_auth":     px_auth,
                    "device_fp":   dev["device_fp"],
                    "os_version":  dev["os_version"],
                    "client_id":   client_id,
                    "email":       email,
                    "phone":       js.get("phone_number", ""),
                    "username":    js.get("username", ""),
                }
                log.info(f"✅ 注册成功：{email} | {acc['phone']} | @{acc['username']}")
                return acc
            else:
                log.warning(f"❌ 注册失败 (尝试 {attempt}/{max_retry})：{resp.status_code} | {resp.text[:200]}")
        except Exception as e:
            log.error(f"❌ 注册异常 (尝试 {attempt}/{max_retry})：{e}")

        if attempt < max_retry:
            backoff = 2 ** (attempt - 1)   # 1s, 2s, 4s...
            log.info(f"   ↳ {backoff}s 后重试…")
            time.sleep(backoff)

    return None


def save_acc(acc):
    """将账号保存到数据库（使用连接池）"""
    if not acc:
        return
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""INSERT INTO accounts
            (cookie, idfa, user_agent, px_auth, device_fp, os_version, client_id, email, phone, username)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (acc["cookie"], acc["idfa"], acc["user_agent"], acc["px_auth"],
             acc["device_fp"], acc["os_version"], acc["client_id"],
             acc["email"], acc["phone"], acc["username"]))
        conn.commit()
        conn.close()
        log.info(f"✅ 已保存账号到数据库: {acc['email']}")
    except Exception as e:
        log.error(f"保存账号失败：{e}")


def batch_reg(num=1):
    """批量注册"""
    init_accounts_schema()
    log.info(f"开始注册 {num} 个账号")
    ok_count = 0
    for i in range(num):
        log.info(f"\n--- 第 {i+1}/{num} 个 ---")
        acc = reg_one()
        if acc:
            save_acc(acc)
            ok_count += 1
        # 每个账号之间随机延时，避免频率过高
        if i < num - 1:
            delay = random.randint(REGISTER_SLEEP_MIN, REGISTER_SLEEP_MAX)
            log.info(f"   ↳ 等待 {delay}s 后注册下一个…")
            time.sleep(delay)
    log.info(f"注册完成：成功 {ok_count}/{num}")


if __name__ == "__main__":
    # 单次注册测试
    batch_reg(1)
    input("\n运行完毕，按回车键退出…")
