import re

with open("tn_web_dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

# 去掉 {% block ... %} 和 {% endblock %} 标签
# 保留标签内的内容
content = re.sub(r"\{%.*?block.*?%\}(.*?)\{%\s*endblock.*?%\}", r"\1", content, flags=re.DOTALL)

with open("tn_web_dashboard.py", "w", encoding="utf-8") as f:
    f.write(content)

print("模板修复完成！已去掉所有 {% block %} 标签。")
