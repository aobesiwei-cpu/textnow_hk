# TextNow 客服系统

一套完整的 TextNow 账号管理 + 客服系统，支持自动回复、Web 控制台、批量注册。

## 📁 文件结构

```
textnow/
├── tn_config.py              # 集中配置（数据库、代理、Web认证等）
├── tn_db.py                  # 数据库连接池 + Schema 初始化
├── tn_customer_service.py    # 客服轮询服务（自动回复）
├── tn_ios_register.py        # iOS 账号注册脚本
├── tn_web_dashboard.py       # Web 控制台（带 Basic Auth）
├── requirements.txt          # 依赖列表
└── README.md                 # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

编辑 `tn_config.py` 或在命令行设置：

```bash
# 数据库
export TN_DB_HOST="170.106.106.252"
export TN_DB_PORT="13306"
export TN_DB_USER="root"
export TN_DB_PASS="你的密码"
export TN_DB_NAME="textnow"

# Web 控制台认证（请务必修改默认密码）
export TN_WEB_USER="admin"
export TN_WEB_PASS="强密码"

# SOCKS5 代理
export TN_PROXY="socks5h://用户名:密码@代理地址:端口"
```

Windows PowerShell:
```powershell
$env:TN_DB_PASS="你的密码"
$env:TN_WEB_PASS="强密码"
```

### 3. 初始化数据库

```bash
python -c "from tn_db import init_accounts_schema; init_accounts_schema()"
```

### 4. 启动服务

**终端 1 - 客服轮询服务：**
```bash
python tn_customer_service.py
```

**终端 2 - Web 控制台：**
```bash
python tn_web_dashboard.py
```

访问 http://localhost:8899，输入用户名/密码登录。

### 5. 注册新账号（按需）

```bash
python tn_ios_register.py
```

## 🔧 功能说明

| 模块 | 功能 |
|------|------|
| `tn_customer_service.py` | 轮询所有账号收件箱，自动回复新消息 |
| `tn_web_dashboard.py` | Web 管理界面：对话管理、模板管理、统计 |
| `tn_ios_register.py` | 批量注册 TextNow iOS 账号 |

## ⚠️ 安全提示

1. **修改默认密码**：`tn_config.py` 中的 `WEB_PASS` 默认是 `admin123`，生产环境务必修改！
2. **数据库密码**：不要提交明文密码到 Git，使用环境变量覆盖
3. **代理安全**：SOCKS5 代理地址不要泄露

## 📝 更新日志

### v2.0
- 统一使用 `tn_config.py` 集中配置
- 统一使用 `tn_db.py` 数据库连接池
- Web 控制台增加 HTTP Basic Auth 认证
- 修复数据库编码问题（utf8mb4）
- 修复 SOCKS5 代理协议（socks5h://）
