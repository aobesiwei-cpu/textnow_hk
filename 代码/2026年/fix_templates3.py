"""修复 tn_web_dashboard.py 的模板系统"""

with open("tn_web_dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在 LAYOUT_TEMPLATE 的 navbar div 后面加一个内容占位符
# 当前 LAYOUT_TEMPLATE 在 navbar div 后面直接是 </body></html>
# 我们需要在 navbar 和 </body> 之间加一个占位符
content = content.replace(
    '</div>\n\n</body>\n</html>\n"""',
    '</div>\n<!-- CONTENT_PLACEHOLDER -->\n</body>\n</html>\n"""',
    1  # 只替换第一个（LAYOUT_TEMPLATE 里的）
)

# 2. 修复 INDEX_TEMPLATE 的 .replace("", ...) 为 .replace("<!-- CONTENT_PLACEHOLDER -->", ...)
content = content.replace(
    'INDEX_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "对话 - TextNow 客服系统").replace(\n"", """',
    'INDEX_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "对话 - TextNow 客服系统").replace(\n"<!-- CONTENT_PLACEHOLDER -->", """',
    1
)

# 3. 修复 ACCOUNTS_TEMPLATE
content = content.replace(
    'ACCOUNTS_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "账号管理 - TextNow 客服系统").replace(\n"", """',
    'ACCOUNTS_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "账号管理 - TextNow 客服系统").replace(\n"<!-- CONTENT_PLACEHOLDER -->", """',
    1
)

# 4. 修复 TEMPLATES_TEMPLATE
content = content.replace(
    'TEMPLATES_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "回复模板 - TextNow 客服系统").replace(\n"", """',
    'TEMPLATES_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "回复模板 - TextNow 客服系统").replace(\n"<!-- CONTENT_PLACEHOLDER -->", """',
    1
)

# 5. 修复 STATS_TEMPLATE
content = content.replace(
    'STATS_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "统计 - TextNow 客服系统").replace(\n"", """',
    'STATS_TEMPLATE = LAYOUT_TEMPLATE.replace("TextNow 客服系统", "统计 - TextNow 客服系统").replace(\n"<!-- CONTENT_PLACEHOLDER -->", """',
    1
)

with open("tn_web_dashboard.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK - 模板占位符已修复")
