import os
import shutil
from datetime import datetime
import time

# 目标目录（请确认路径正确）
target_dir = r"C:\Users\carti\Documents\textnow"

# 定义文件类型分类（可根据需要扩展）
file_categories = {
    "文档": [".txt", ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx"],
    "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"],
    "音频": [".mp3", ".wav", ".flac", ".m4a"],
    "视频": [".mp4", ".avi", ".mov", ".mkv"],
    "压缩包": [".zip", ".rar", ".7z", ".tar"],
    "代码": [".py", ".java", ".cpp", ".js", ".html", ".css"],
}

# 整理日志（记录操作）
log_file = os.path.join(target_dir, "文件整理日志.txt")

def init_log():
    """初始化日志文件"""
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"文件整理日志 - 开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*50 + "\n")

def write_log(content):
    """写入日志"""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {content}\n")

def get_file_modify_time(file_path):
    """获取文件修改时间（格式化成年份）"""
    modify_time = os.path.getmtime(file_path)
    modify_year = datetime.fromtimestamp(modify_time).strftime("%Y年")
    return modify_year

def get_file_category(file_ext):
    """根据扩展名获取文件分类"""
    for category, exts in file_categories.items():
        if file_ext.lower() in exts:
            return category
    return "其他文件"

def get_unique_filename(dir_path, filename):
    """处理重复文件名，生成唯一名称"""
    name, ext = os.path.splitext(filename)
    new_filename = filename
    count = 1
    while os.path.exists(os.path.join(dir_path, new_filename)):
        new_filename = f"{name}_{count}{ext}"
        count += 1
    return new_filename

def organize_files():
    """核心整理逻辑"""
    # 检查目标目录是否存在
    if not os.path.exists(target_dir):
        print(f"错误：目录 {target_dir} 不存在！")
        return

    # 初始化日志
    init_log()
    write_log(f"开始整理目录：{target_dir}")

    # 遍历目录下所有文件（不递归子目录，避免重复整理）
    for filename in os.listdir(target_dir):
        file_path = os.path.join(target_dir, filename)
        
        # 跳过文件夹、日志文件本身
        if os.path.isdir(file_path) or filename == "文件整理日志.txt":
            continue

        # 获取文件信息
        file_ext = os.path.splitext(filename)[1]
        file_category = get_file_category(file_ext)
        file_year = get_file_modify_time(file_path)

        # 构建目标子文件夹路径（分类/年份）
        dest_dir = os.path.join(target_dir, file_category, file_year)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            write_log(f"创建文件夹：{dest_dir}")

        # 生成唯一文件名（避免重复）
        dest_filename = get_unique_filename(dest_dir, filename)
        dest_path = os.path.join(dest_dir, dest_filename)

        # 移动文件
        try:
            shutil.move(file_path, dest_path)
            write_log(f"移动文件：{filename} -> {dest_path}")
            print(f"成功整理：{filename} -> {dest_dir}\\{dest_filename}")
        except Exception as e:
            error_msg = f"整理失败 {filename}：{str(e)}"
            write_log(error_msg)
            print(f"错误：{error_msg}")

    write_log("文件整理完成！")
    print("\n整理完成！日志文件路径：", log_file)

if __name__ == "__main__":
    # 确认是否执行整理
    confirm = input(f"即将整理目录：{target_dir}\n是否继续？(y/n)：")
    if confirm.lower() == "y":
        organize_files()
    else:
        print("操作已取消。")