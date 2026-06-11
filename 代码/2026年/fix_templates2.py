with open("tn_web_dashboard.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

fixed_lines = []
for line in lines:
    # 去掉 {% block ... %} 和 {% endblock ... %} 行
    if "{% block" in line or "{% endblock" in line:
        continue
    # 去掉行内嵌的 {% block title %}...{% endblock %} 等
    while "{% " in line:
        idx = line.find("{% ")
        if idx == -1:
            break
        end_idx = line.find("%}", idx)
        if end_idx == -1:
            break
        line = line[:idx] + line[end_idx+2:]
    fixed_lines.append(line)

with open("tn_web_dashboard.py", "w", encoding="utf-8") as f:
    f.writelines(fixed_lines)

print("修复完成！已去掉所有 {% block %} 标签。")
