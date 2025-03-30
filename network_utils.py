import socket
import os

def get_local_ip():
    """Get the local IP address of the server."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS に接続して自身のローカルIPを取得
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"  # 失敗時のフォールバック
    

def get_server_ip():
    """Return HOST_IP from env if exists, otherwise fallback to local IP."""
    return os.environ.get("HOST_IP", get_local_ip())


def get_server_url():
    """Return the server URL based on the environment variable or local IP."""
    server_ip = get_server_ip()
    if "playground.com" in server_ip:
        return f"https://{server_ip}"
    else:
        return f"http://{server_ip}:3000"