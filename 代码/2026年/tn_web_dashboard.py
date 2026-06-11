"""
TextNow 客服系统 - Web 控制台（坐席界面）v2
Flask 应用，提供对话管理、模板回复、实时监控功能。

改进：
  1. 使用 tn_config 集中配置
  2. 使用 tn_db 连接池
  3. 增加 HTTP Basic Auth 认证
  4. 修复统计接口逻辑

启动方式：
    pip install flask pymysql
    python tn_web_dashboard.py
"""
from functools import wraps
from flask import Flask, render_template_string, request, jsonify, Response
import pymysql
import logging

from tn_config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, WEB_HOST, WEB_PORT, WEB_USER, WEB_PASS, PROXY
from tn_db import get_db, get_db_dict

app = Flask(__name__)

# ===================== 日志 =====================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ===================== Basic Auth =====================
def check_auth(username, password):
    """验证用户名密码"""
    return username == WEB_USER and password == WEB_PASS


def authenticate():
    """返回 401 响应要求认证"""
    return Response(
        '需要登录才能访问\n请使用正确的用户名和密码',
        401,
        {'WWW-Authenticate': 'Basic realm="TextNow 客服系统"'}
    )


def requires_auth(f):
    """装饰器：要求 HTTP Basic Auth"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# ===================== HTML 模板 =====================
LAYOUT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TextNow 客服系统</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; }
  .navbar { background: #1a1a2e; color: white; padding: 12px 24px; display: flex; align-items: center; gap: 20px; }
  .navbar h1 { font-size: 18px; font-weight: 600; }
  .navbar .status { margin-left: auto; display: flex; align-items: center; gap: 8px; font-size: 13px; color: #aaa; }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  .container { display: flex; height: calc(100vh - 52px); }
  /* 左侧边栏 - 对话列表 */
  .sidebar { width: 320px; background: white; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; }
  .sidebar-header { padding: 16px; border-bottom: 1px solid #e5e7eb; display: flex; gap: 8px; }
  .sidebar-header input { flex: 1; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; }
  .badge { background: #ef4444; color: white; font-size: 11px; padding: 2px 7px; border-radius: 10px; }
  .conv-list { flex: 1; overflow-y: auto; }
  .conv-item { padding: 14px 16px; border-bottom: 1px solid #f3f4f6; cursor: pointer; transition: background 0.15s; }
  .conv-item:hover { background: #f9fafb; }
  .conv-item.active { background: #eef2ff; border-right: 3px solid #4f46e5; }
  .conv-item .top { display: flex; justify-content: space-between; align-items: center; }
  .conv-item .number { font-weight: 600; font-size: 14px; }
  .conv-item .time { font-size: 11px; color: #9ca3af; }
  .conv-item .preview { font-size: 13px; color: #6b7280; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .conv-item.unread .number { color: #4f46e5; }
  .conv-item.unread .preview { color: #374151; font-weight: 500; }
  .filter-tabs { display: flex; padding: 8px 12px; gap: 4px; border-bottom: 1px solid #e5e7eb; }
  .filter-tab { font-size: 12px; padding: 4px 10px; border-radius: 12px; cursor: pointer; color: #6b7280; }
  .filter-tab.active { background: #4f46e5; color: white; }
  /* 中间 - 聊天区域 */
  .chat-area { flex: 1; display: flex; flex-direction: column; background: #f9fafb; }
  .chat-header { padding: 14px 20px; background: white; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; gap: 12px; }
  .chat-header .avatar { width: 36px; height: 36px; border-radius: 50%; background: #4f46e5; color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; }
  .chat-header .info .name { font-weight: 600; font-size: 14px; }
  .chat-header .info .meta { font-size: 12px; color: #9ca3af; }
  .chat-header .actions { margin-left: auto; display: flex; gap: 8px; }
  .btn { padding: 6px 14px; border-radius: 8px; border: 1px solid #e5e7eb; background: white; cursor: pointer; font-size: 13px; }
  .btn-primary { background: #4f46e5; color: white; border-color: #4f46e5; }
  .btn-danger { color: #ef4444; border-color: #fecaca; }
  .message-list { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
  .msg { max-width: 70%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5; }
  .msg.in { align-self: flex-start; background: white; border: 1px solid #e5e7eb; border-bottom-left-radius: 4px; }
  .msg.out { align-self: flex-end; background: #4f46e5; color: white; border-bottom-right-radius: 4px; }
  .msg .meta { font-size: 11px; color: #9ca3af; margin-top: 4px; }
  .msg.out .meta { color: rgba(255,255,255,0.7); }
  .msg.auto { font-style: italic; }
  .reply-box { padding: 14px 20px; background: white; border-top: 1px solid #e5e7eb; }
  .reply-row { display: flex; gap: 8px; align-items: flex-end; }
  .reply-row textarea { flex: 1; padding: 10px 14px; border: 1px solid #e5e7eb; border-radius: 10px; font-size: 14px; resize: none; min-height: 42px; }
  .template-bar { display: flex; gap: 6px; padding: 8px 0; flex-wrap: wrap; }
  .tpl-chip { font-size: 12px; padding: 4px 10px; border-radius: 14px; background: #f3f4f6; color: #374151; cursor: pointer; border: 1px solid #e5e7eb; }
  .tpl-chip:hover { background: #eef2ff; color: #4f46e5; }
  /* 右侧边栏 - 联系人信息 + 模板 */
  .right-sidebar { width: 280px; background: white; border-left: 1px solid #e5e7eb; padding: 20px; overflow-y: auto; }
  .right-sidebar h3 { font-size: 13px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
  .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f9fafb; font-size: 13px; }
  .info-row .label { color: #9ca3af; }
  .info-row .value { font-weight: 500; }
  .tpl-list { margin-top: 8px; }
  .tpl-item { padding: 10px; background: #f9fafb; border-radius: 8px; margin-bottom: 8px; cursor: pointer; border: 1px solid transparent; }
  .tpl-item:hover { border-color: #4f46e5; background: #eef2ff; }
  .tpl-item .tpl-name { font-size: 12px; color: #9ca3af; }
  .tpl-item .tpl-content { font-size: 13px; margin-top: 4px; color: #374151; }
  .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #9ca3af; }
  .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
  /* 统计卡片 */
  .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 20px; }
  .stat-card { background: white; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb; }
  .stat-card .label { font-size: 13px; color: #9ca3af; }
  .stat-card .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
  .stat-card .sub { font-size: 12px; color: #22c55e; margin-top: 4px; }
  .accounts-table { background: white; margin: 0 20px 20px; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden; }
  .accounts-table table { width: 100%; border-collapse: collapse; }
  .accounts-table th { background: #f9fafb; padding: 10px 16px; text-align: left; font-size: 12px; color: #9ca3af; text-transform: uppercase; }
  .accounts-table td { padding: 12px 16px; font-size: 13px; border-top: 1px solid #f3f4f6; }
  .tag { font-size: 11px; padding: 2px 8px; border-radius: 8px; }
  .tag-active { background: #dcfce7; color: #16a34a; }
  .tag-inactive { background: #f3f4f6; color: #9ca3af; }
  .tag-auto { background: #eef2ff; color: #4f46e5; }
</style>

</head>
<body>
<div class="navbar">
  <h1>📱 TextNow 客服系统</h1>
  <a href="/" style="color:#aaa; text-decoration:none; font-size:13px;">💬 对话</a>
  <a href="/accounts" style="color:#aaa; text-decoration:none; font-size:13px;">📋 账号</a>
  <a href="/templates" style="color:#aaa; text-decoration:none; font-size:13px;">📝 模板</a>
  <a href="/stats" style="color:#aaa; text-decoration:none; font-size:13px;">📊 统计</a>
  <div class="status">
    <div class="status-dot"></div>
    <span>服务运行中</span>
  </div>
</div>
<!-- CONTENT_PLACEHOLDER -->
</body>
</html>
"""

INDEX_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "对话 - TextNow 客服系统").replace(
"<!-- CONTENT_PLACEHOLDER -->", """
<div class="container">
  <!-- 左侧：对话列表 -->
  <div class="sidebar">
    <div class="sidebar-header">
      <input type="text" placeholder="搜索对话..." id="searchInput" onkeyup="filterConversations()">
      <span class="badge" id="unreadBadge">0</span>
    </div>
    <div class="filter-tabs">
      <span class="filter-tab active" onclick="filterByStatus('all', this)">全部</span>
      <span class="filter-tab" onclick="filterByStatus('1', this)">活跃</span>
      <span class="filter-tab" onclick="filterByStatus('3', this)">待人工</span>
      <span class="filter-tab" onclick="filterByStatus('2', this)">已关闭</span>
    </div>
    <div class="conv-list" id="convList"></div>
  </div>

  <!-- 中间：聊天区域 -->
  <div class="chat-area" id="chatArea">
    <div class="empty-state" id="emptyState">
      <div class="icon">💬</div>
      <p>选择一个对话开始回复</p>
      <p style="font-size:12px;margin-top:8px;">左侧列表会实时刷新新消息</p>
    </div>
    <div id="chatContent" style="display:none; flex:1; display:none; flex-direction:column; height:100%;">
      <div class="chat-header" id="chatHeader"></div>
      <div class="message-list" id="messageList"></div>
      <div class="reply-box">
        <div class="template-bar" id="templateBar"></div>
        <div class="reply-row">
          <textarea id="replyInput" placeholder="输入回复内容... 支持 /模板快捷指令" rows="1"></textarea>
          <button class="btn btn-primary" onclick="sendReply()">发送</button>
        </div>
        <div style="font-size:11px;color:#9ca3af;margin-top:6px;">
          提示：输入 / 查看模板快捷指令，按 Enter 发送，Shift+Enter 换行
        </div>
      </div>
    </div>
  </div>

  <!-- 右侧：联系信息 + 模板 -->
  <div class="right-sidebar" id="rightSidebar" style="display:none;">
    <h3>联系人信息</h3>
    <div id="contactInfo"></div>
    <h3 style="margin-top:24px;">快捷模板</h3>
    <div class="tpl-list" id="tplList"></div>
  </div>
</div>

<script>
let currentConvId = null;
let currentAcc = null;
let pollTimer = null;
let statusFilter = 'all';

async function loadConversations() {
  const res = await fetch('/api/conversations?status=' + statusFilter);
  const data = await res.json();
  const list = document.getElementById('convList');
  list.innerHTML = '';
  let unread = 0;
  data.forEach(c => {
    if (c.unread_count > 0) unread += c.unread_count;
    const div = document.createElement('div');
    div.className = 'conv-item' + (c.unread_count > 0 ? ' unread' : '') + (currentConvId == c.id ? ' active' : '');
    div.onclick = () => openConversation(c.id);
    div.innerHTML = `
      <div class="top">
        <span class="number">${c.contact_number}</span>
        <span class="time">${c.last_time_str || ''}</span>
      </div>
      <div class="preview">${c.last_preview || '暂无消息'}</div>
      ${c.unread_count > 0 ? '<span class="badge">'+c.unread_count+'</span>' : ''}
    `;
    list.appendChild(div);
  });
  document.getElementById('unreadBadge').textContent = unread;
}

async function openConversation(convId) {
  currentConvId = convId;
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('chatContent').style.display = 'flex';
  document.getElementById('rightSidebar').style.display = 'block';
  await loadMessages();
  await loadContactInfo();
  await loadTemplates();
  loadConversations();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(loadMessages, 5000);
}

async function loadMessages() {
  if (!currentConvId) return;
  const res = await fetch('/api/messages?conv_id=' + currentConvId);
  const data = await res.json();
  const list = document.getElementById('messageList');
  list.innerHTML = '';
  data.forEach(m => {
    const div = document.createElement('div');
    div.className = 'msg ' + (m.direction == 1 ? 'in' : 'out') + (m.is_auto_reply ? ' auto' : '');
    div.innerHTML = '<div>' + escapeHtml(m.content) + '</div><div class="meta">' + m.sent_time_str + (m.is_auto_reply ? ' · 自动回复' : '') + '</div>';
    list.appendChild(div);
  });
  list.scrollTop = list.scrollHeight;
  // 标记已读
  fetch('/api/mark_read', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({conv_id: currentConvId})});
}

async function loadContactInfo() {
  const res = await fetch('/api/conversations/' + currentConvId);
  const data = await res.json();
  document.getElementById('chatHeader').innerHTML = `
    <div class="avatar">${(data.contact_number || '?').slice(-2)}</div>
    <div class="info">
      <div class="name">${data.contact_number}</div>
      <div class="meta">${data.contact_username || ''} · 使用账号: ${data.account_phone || data.account_email || ''}</div>
    </div>
    <div class="actions">
      <button class="btn ${data.status==2?'':'btn-danger'}" onclick="closeConversation()">${data.status==2?'已关闭':'关闭对话'}</button>
    </div>
  `;
  document.getElementById('contactInfo').innerHTML = `
    <div class="info-row"><span class="label">客户号码</span><span class="value">${data.contact_number}</span></div>
    <div class="info-row"><span class="label">用户名</span><span class="value">${data.contact_username||'-'}</span></div>
    <div class="info-row"><span class="label">状态</span><span class="value">${data.status==1?'🟢 活跃':data.status==2?'⚫ 已关闭':'🟡 待人工'}</span></div>
    <div class="info-row"><span class="label">消息数</span><span class="value">${data.msg_count||0}</span></div>
    <div class="info-row"><span class="label">创建时间</span><span class="value">${data.created_time_str||''}</span></div>
  `;
}

async function loadTemplates() {
  const res = await fetch('/api/templates');
  const data = await res.json();
  const bar = document.getElementById('templateBar');
  const list = document.getElementById('tplList');
  bar.innerHTML = '';
  list.innerHTML = '';
  data.forEach(t => {
    const chip = document.createElement('span');
    chip.className = 'tpl-chip';
    chip.textContent = t.shortcut;
    chip.title = t.content;
    chip.onclick = () => insertTemplate(t.content);
    bar.appendChild(chip);
    const item = document.createElement('div');
    item.className = 'tpl-item';
    item.innerHTML = `<div class="tpl-name">${t.name} (${t.shortcut})</div><div class="tpl-content">${t.content}</div>`;
    item.onclick = () => insertTemplate(t.content);
    list.appendChild(item);
  });
}

function insertTemplate(content) {
  document.getElementById('replyInput').value = content;
  document.getElementById('replyInput').focus();
}

async function sendReply() {
  const input = document.getElementById('replyInput');
  const content = input.value.trim();
  if (!content || !currentConvId) return;
  const res = await fetch('/api/send_reply', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({conv_id: currentConvId, content: content})
  });
  const result = await res.json();
  if (result.success) {
    input.value = '';
    await loadMessages();
  } else {
    alert('发送失败: ' + (result.error || '未知错误'));
  }
}

async function closeConversation() {
  if (!currentConvId) return;
  await fetch('/api/conversations/' + currentConvId + '/close', {method:'POST'});
  await loadContactInfo();
}

function filterByStatus(status, el) {
  statusFilter = status;
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  loadConversations();
}

function filterConversations() {
  const q = document.getElementById('searchInput').value.toLowerCase();
  document.querySelectorAll('.conv-item').forEach(item => {
    item.style.display = item.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML.replace(/\\n/g, '<br>');
}

// Enter 发送
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey && document.activeElement.id === 'replyInput') {
    e.preventDefault();
    sendReply();
  }
});

// 初始加载
loadConversations();
setInterval(loadConversations, 10000);
</script>

"""
)

ACCOUNTS_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "账号管理 - TextNow 客服系统").replace(
"<!-- CONTENT_PLACEHOLDER -->", """
<div style="padding:20px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <h2 style="font-size:20px; font-weight:600;">📋 TextNow 账号管理</h2>
    <button class="btn btn-primary" onclick="alert('请在 tn_ios_register.py 中注册新账号')">+ 注册新账号</button>
  </div>
  <div class="accounts-table">
    <table>
      <thead><tr><th>ID</th><th>手机号</th><th>邮箱</th><th>用户名</th><th>IDFA</th><th>状态</th><th>注册时间</th></tr></thead>
      <tbody id="accTableBody"></tbody>
    </table>
  </div>
</div>
<script>
async function loadAccounts() {
  const res = await fetch('/api/accounts');
  const data = await res.json();
  const tbody = document.getElementById('accTableBody');
  tbody.innerHTML = '';
  data.forEach(a => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${a.id}</td>
      <td><strong>${a.phone || '-'}</strong></td>
      <td>${a.email}</td>
      <td>${a.username || '-'}</td>
      <td style="font-size:11px;color:#9ca3af;">${(a.idfa||'-').slice(0,8)}...</td>
      <td><span class="tag ${a.status==1?'tag-active':'tag-inactive'}">${a.status==1?'活跃':'停用'}</span></td>
      <td style="font-size:12px;color:#9ca3af;">${a.create_time_str || ''}</td>
    `;
    tbody.appendChild(tr);
  });
}
loadAccounts();
setInterval(loadAccounts, 30000);
</script>

"""
)

TEMPLATES_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "回复模板 - TextNow 客服系统").replace(
"<!-- CONTENT_PLACEHOLDER -->", """
<div style="padding:20px; max-width:800px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <h2 style="font-size:20px; font-weight:600;">📝 回复模板管理</h2>
    <button class="btn btn-primary" onclick="showAddTemplate()">+ 新增模板</button>
  </div>
  <div id="tplCards" style="display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:16px;"></div>
</div>

<div id="addModal" style="display:none; position:fixed; top:0;left:0;right:0;bottom:0; background:rgba(0,0,0,0.5); z-index:100;">
  <div style="background:white; max-width:500px; margin:100px auto; border-radius:16px; padding:24px;">
    <h3 style="margin-bottom:16px;">新增/编辑模板</h3>
    <input id="tplName" placeholder="模板名称" style="width:100%;padding:8px 12px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:12px;">
    <input id="tplShortcut" placeholder="快捷指令 (如 /welcome)" style="width:100%;padding:8px 12px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:12px;">
    <select id="tplCategory" style="width:100%;padding:8px 12px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:12px;">
      <option value="greeting">问候</option>
      <option value="price">价格</option>
      <option value="support">技术支持</option>
      <option value="close">结束语</option>
      <option value="other">其他</option>
    </select>
    <textarea id="tplContent" placeholder="模板内容（支持换行）" style="width:100%;padding:10px 12px;border:1px solid #e5e7eb;border-radius:8px;min-height:100px;margin-bottom:16px;"></textarea>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn" onclick="document.getElementById('addModal').style.display='none'">取消</button>
      <button class="btn btn-primary" onclick="saveTemplate()">保存</button>
    </div>
  </div>
</div>

<script>
let editingId = null;

async function loadTemplates() {
  const res = await fetch('/api/templates');
  const data = await res.json();
  const grid = document.getElementById('tplCards');
  grid.innerHTML = '';
  data.forEach(t => {
    const card = document.createElement('div');
    card.style.cssText = 'background:white; border-radius:12px; padding:20px; border:1px solid #e5e7eb;';
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span class="tag tag-auto">${t.category||'other'}</span>
        <span style="font-size:12px;color:#9ca3af;">${t.shortcut}</span>
      </div>
      <div style="font-weight:600;margin-bottom:8px;">${t.name}</div>
      <div style="font-size:13px;color:#6b7280;line-height:1.6;white-space:pre-wrap;">${t.content}</div>
      <div style="display:flex;gap:8px;margin-top:16px;">
        <button class="btn" onclick="editTemplate(${t.id})">编辑</button>
        <button class="btn btn-danger" onclick="deleteTemplate(${t.id})">删除</button>
      </div>
    `;
    grid.appendChild(card);
  });
}

function showAddTemplate() {
  editingId = null;
  document.getElementById('tplName').value = '';
  document.getElementById('tplShortcut').value = '';
  document.getElementById('tplContent').value = '';
  document.getElementById('addModal').style.display = 'block';
}

async function editTemplate(id) {
  const res = await fetch('/api/templates');
  const data = await res.json();
  const t = data.find(x => x.id == id);
  if (!t) return;
  editingId = id;
  document.getElementById('tplName').value = t.name;
  document.getElementById('tplShortcut').value = t.shortcut;
  document.getElementById('tplCategory').value = t.category || 'other';
  document.getElementById('tplContent').value = t.content;
  document.getElementById('addModal').style.display = 'block';
}

async function saveTemplate() {
  const name = document.getElementById('tplName').value.trim();
  const shortcut = document.getElementById('tplShortcut').value.trim();
  const category = document.getElementById('tplCategory').value;
  const content = document.getElementById('tplContent').value.trim();
  if (!name || !shortcut || !content) { alert('请填写完整'); return; }
  await fetch('/api/templates' + (editingId ? '/' + editingId : ''), {
    method: editingId ? 'PUT' : 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, shortcut, category, content})
  });
  document.getElementById('addModal').style.display = 'none';
  loadTemplates();
}

async function deleteTemplate(id) {
  if (!confirm('确认删除此模板？')) return;
  await fetch('/api/templates/' + id, {method:'DELETE'});
  loadTemplates();
}

loadTemplates();
</script>

"""
)

STATS_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "统计 - TextNow 客服系统").replace(
"<!-- CONTENT_PLACEHOLDER -->", """
<div style="padding:20px;">
  <h2 style="font-size:20px;font-weight:600;margin-bottom:20px;">📊 数据统计</h2>
  <div class="stats-grid" id="statsGrid"></div>
  <div style="background:white;border-radius:12px;border:1px solid #e5e7eb;padding:24px;margin:0 0 20px;">
    <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">最近活动</h3>
    <div id="recentActivity"></div>
  </div>
</div>
<script>
async function loadStats() {
  const res = await fetch('/api/stats');
  const s = await res.json();
  document.getElementById('statsGrid').innerHTML = `
    <div class="stat-card"><div class="label">活跃对话</div><div class="value" style="color:#4f46e5;">${s.active_conversations||0}</div><div class="sub">↗ 较昨日 +${s.active_conversations_delta||0}</div></div>
    <div class="stat-card"><div class="label">今日消息</div><div class="value">${s.today_messages||0}</div><div class="sub">自动回复: ${s.today_auto_replies||0}</div></div>
    <div class="stat-card"><div class="label">可用账号</div><div class="value" style="color:#22c55e;">${s.active_accounts||0}</div><div class="sub">总计 ${s.total_accounts||0} 个</div></div>
    <div class="stat-card"><div class="label">自动回复率</div><div class="value" style="color:#f59e0b;">${s.auto_reply_rate||0}%</div><div class="sub">模板数: ${s.template_count||0}</div></div>
  `;
  const act = document.getElementById('recentActivity');
  act.innerHTML = (s.recent_messages||[]).map(m => `
    <div style="display:flex;padding:10px 0;border-bottom:1px solid #f9fafb;font-size:13px;">
      <span style="color:#9ca3af;width:140px;">${m.sent_time_str}</span>
      <span>${m.direction==1?'📥':'📤'}</span>
      <span style="margin-left:8px;flex:1;">${m.content.substring(0,60)}</span>
      <span style="color:#9ca3af;">${m.contact_number}</span>
    </div>
  `).join('');
}
loadStats();
setInterval(loadStats, 30000);
</script>

"""
)


# ===================== API 路由 =====================

@app.route("/")
@requires_auth
def index():
    return INDEX_TEMPLATE


@app.route("/accounts")
@requires_auth
def accounts_page():
    return ACCOUNTS_TEMPLATE


@app.route("/templates")
@requires_auth
def templates_page():
    return TEMPLATES_TEMPLATE


@app.route("/stats")
@requires_auth
def stats_page():
    return STATS_TEMPLATE


@app.route("/api/conversations")
@requires_auth
def api_conversations():
    status = request.args.get("status", "all")
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    sql = """
        SELECT c.*,
               (SELECT content FROM messages WHERE conversation_id=c.id ORDER BY sent_time DESC LIMIT 1) as last_preview,
               (SELECT DATE_FORMAT(sent_time,'%%Y-%%m-%%d %%H:%%i') FROM messages WHERE conversation_id=c.id ORDER BY sent_time DESC LIMIT 1) as last_time_str,
               (SELECT COUNT(*) FROM messages WHERE conversation_id=c.id AND direction=1 AND read_status=0) as unread_count,
               (SELECT COUNT(*) FROM messages WHERE conversation_id=c.id) as msg_count,
               a.phone as account_phone, a.email as account_email
        FROM conversations c
        LEFT JOIN accounts a ON c.account_id=a.id
    """
    params = []
    if status != "all":
        sql += " WHERE c.status=%s"
        params.append(int(status))
    sql += " ORDER BY c.last_message_time DESC LIMIT 200"
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    for r in rows:
        r["last_time_str"] = r.get("last_time_str") or (r.get("last_message_time") and r["last_message_time"].strftime("%H:%M"))
    return jsonify(rows)


@app.route("/api/conversations/<int:conv_id>")
@requires_auth
def api_conversation_detail(conv_id):
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("""SELECT c.*, a.phone as account_phone, a.email as account_email,
                          (SELECT COUNT(*) FROM messages WHERE conversation_id=c.id) as msg_count
                   FROM conversations c
                   LEFT JOIN accounts a ON c.account_id=a.id
                   WHERE c.id=%s""", (conv_id,))
    row = cur.fetchone()
    if row and row.get("created_time"):
        row["created_time_str"] = row["created_time"].strftime("%Y-%m-%d %H:%M")
    conn.close()
    return jsonify(row or {})


@app.route("/api/conversations/<int:conv_id>/close", methods=["POST"])
@requires_auth
def api_close_conversation(conv_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE conversations SET status=2 WHERE id=%s", (conv_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/messages")
@requires_auth
def api_messages():
    conv_id = request.args.get("conv_id", type=int)
    if not conv_id:
        return jsonify([])
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("""SELECT * FROM messages WHERE conversation_id=%s ORDER BY sent_time ASC LIMIT 500""", (conv_id,))
    rows = cur.fetchall()
    conn.close()
    for r in rows:
        r["sent_time_str"] = r["sent_time"].strftime("%H:%M") if r.get("sent_time") else ""
    return jsonify(rows)


@app.route("/api/mark_read", methods=["POST"])
@requires_auth
def api_mark_read():
    data = request.get_json()
    conv_id = data.get("conv_id")
    if not conv_id:
        return jsonify({"success": False})
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE messages SET read_status=1 WHERE conversation_id=%s AND direction=1", (conv_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/send_reply", methods=["POST"])
@requires_auth
def api_send_reply():
    data = request.get_json()
    conv_id = data.get("conv_id")
    content = data.get("content", "").strip()
    if not conv_id or not content:
        return jsonify({"success": False, "error": "参数不完整"})

    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT contact_number, account_id, status FROM conversations WHERE id=%s", (conv_id,))
    conv = cur.fetchone()
    if not conv:
        conn.close()
        return jsonify({"success": False, "error": "对话不存在"})

    cur.execute("SELECT * FROM accounts WHERE id=%s", (conv["account_id"],))
    acc = cur.fetchone()
    conn.close()

    if not acc:
        return jsonify({"success": False, "error": "账号不存在"})

    # 调用 TextNow 发送
    try:
        import requests
        headers = {
            "Host": "api.textnow.me",
            "Content-Type": "application/json",
            "User-Agent": acc["user_agent"],
            "X-Idfa": acc["idfa"],
            "X-Client-ID": acc["client_id"],
            "X-PX-Auth": acc["px_auth"],
            "X-Device-FP": acc["device_fp"],
            "Cookie": acc["cookie"],
            "Accept": "application/json",
            "Accept-Language": "en-US",
        }
        resp = requests.post(
            f"https://api.textnow.me/api/v2/users/{acc['username']}/messages",
            headers=headers,
            json={"to": conv["contact_number"], "content": content, "message_type": "text"},
            proxies=PROXY,
            timeout=20
        )
        if resp.status_code in (200, 201):
            # 保存发出消息
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages (conversation_id, direction, content, is_auto_reply, sent_time) VALUES (%s,2,%s,0,NOW())",
                (conv_id, content)
            )
            cur.execute("UPDATE conversations SET last_message_time=NOW() WHERE id=%s", (conv_id,))
            conn.commit()
            conn.close()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": f"API错误 {resp.status_code}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/accounts")
@requires_auth
def api_accounts():
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT *, DATE_FORMAT(create_time,'%Y-%m-%d %H:%i') as create_time_str FROM accounts ORDER BY id DESC LIMIT 500")
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)


@app.route("/api/templates", methods=["GET"])
@requires_auth
def api_get_templates():
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM reply_templates WHERE is_active=1 ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)


@app.route("/api/templates", methods=["POST"])
@requires_auth
def api_add_template():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reply_templates (name, shortcut, content, category) VALUES (%s,%s,%s,%s)",
        (data["name"], data["shortcut"], data["content"], data.get("category", "other"))
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/templates/<int:tpl_id>", methods=["PUT"])
@requires_auth
def api_update_template(tpl_id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE reply_templates SET name=%s, shortcut=%s, content=%s, category=%s WHERE id=%s",
        (data["name"], data["shortcut"], data["content"], data.get("category", "other"), tpl_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/templates/<int:tpl_id>", methods=["DELETE"])
@requires_auth
def api_delete_template(tpl_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE reply_templates SET is_active=0 WHERE id=%s", (tpl_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/stats")
@requires_auth
def api_stats():
    conn = get_db_dict()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    stats = {}
    cur.execute("SELECT COUNT(*) as c FROM conversations WHERE status=1")
    stats["active_conversations"] = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM conversations WHERE DATE(last_message_time)=CURDATE()")
    stats["active_conversations_delta"] = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM messages WHERE direction=2 AND DATE(sent_time)=CURDATE()")
    stats["today_messages"] = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM messages WHERE direction=2 AND is_auto_reply=1 AND DATE(sent_time)=CURDATE()")
    stats["today_auto_replies"] = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM accounts WHERE status=1")
    stats["active_accounts"] = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM accounts")
    stats["total_accounts"] = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM reply_templates WHERE is_active=1")
    stats["template_count"] = cur.fetchone()["c"]
    rate = 0
    if stats["today_messages"] > 0:
        rate = int(stats["today_auto_replies"] / stats["today_messages"] * 100)
    stats["auto_reply_rate"] = rate

    cur.execute("""SELECT m.*, c.contact_number FROM messages m
                   LEFT JOIN conversations c ON m.conversation_id=c.id
                   ORDER BY m.sent_time DESC LIMIT 20""")
    recent = cur.fetchall()
    for r in recent:
        r["sent_time_str"] = r["sent_time"].strftime("%H:%M") if r.get("sent_time") else ""
    stats["recent_messages"] = recent
    conn.close()
    return jsonify(stats)


if __name__ == "__main__":
    log.info(f"🚀 Web 控制台启动: http://{WEB_HOST}:{WEB_PORT}")
    log.info(f"   默认登录账号: {WEB_USER} / {WEB_PASS}")
    log.warning("⚠️  生产环境请修改默认密码！")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
