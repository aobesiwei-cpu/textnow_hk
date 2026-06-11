import paramiko
import os

HOST = "170.106.106.252"
PORT = 22
USER = "root"
PASS = "Ws961230&@^%#&!"

def main():
    # 连接服务器
    print(f"Connecting to {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, PORT, USER, PASS, timeout=30)
    print("Connected!")
    
    # 检查现有目录
    stdin, stdout, stderr = client.exec_command("ls -la /root/textnow 2>/dev/null || echo 'NOT_EXISTS'")
    result = stdout.read().decode().strip()
    print(f"Check /root/textnow: {result[:100]}")
    
    # 创建目录
    stdin, stdout, stderr = client.exec_command("mkdir -p /root/textnow")
    print("Created /root/textnow")
    
    # 上传文件
    sftp = client.open_sftp()
    local_files = [
        "tn_web_dashboard.py",
        "tn_db.py", 
        "tn_config.py",
        "init_accounts_schema.py"
    ]
    
    for fname in local_files:
        if os.path.exists(fname):
            remote_path = f"/root/textnow/{fname}"
            print(f"Uploading {fname}...")
            sftp.put(fname, remote_path)
            print(f"  -> {remote_path}")
    
    sftp.close()
    
    # 检查 Python 环境
    stdin, stdout, stderr = client.exec_command("which python3 && python3 --version")
    py_result = stdout.read().decode().strip()
    print(f"Python: {py_result}")
    
    # 安装依赖
    print("Installing dependencies...")
    stdin, stdout, stderr = client.exec_command("pip3 install flask pymysql dbutils 2>&1")
    pip_result = stdout.read().decode()
    print(f"pip install: {pip_result[:200]}")
    
    # 检查防火墙
    stdin, stdout, stderr = client.exec_command("firewall-cmd --list-ports 2>/dev/null || echo 'firewall-cmd not available'")
    fw_result = stdout.read().decode().strip()
    print(f"Firewall ports: {fw_result}")
    
    # 开放 8899 端口
    print("Opening port 8899...")
    stdin, stdout, stderr = client.exec_command("firewall-cmd --add-port=8899/tcp --permanent 2>&1 && firewall-cmd --reload 2>&1")
    fw_open = stdout.read().decode().strip()
    print(f"Firewall result: {fw_open}")
    
    # 启动 Flask
    print("Starting Flask...")
    stdin, stdout, stderr = client.exec_command("cd /root/textnow && nohup python3 tn_web_dashboard.py > /root/textnow/flask.log 2>&1 &")
    print("Flask started in background")
    
    # 检查进程
    import time
    time.sleep(2)
    stdin, stdout, stderr = client.exec_command("ps aux | grep tn_web_dashboard | grep -v grep")
    ps_result = stdout.read().decode().strip()
    print(f"Process: {ps_result}")
    
    # 检查端口监听
    stdin, stdout, stderr = client.exec_command("netstat -tlnp | grep 8899 || ss -tlnp | grep 8899")
    port_result = stdout.read().decode().strip()
    print(f"Port 8899: {port_result}")
    
    client.close()
    print("\nDeployment complete!")
    print("Try accessing: http://170.106.106.252:8899/")

if __name__ == "__main__":
    main()
