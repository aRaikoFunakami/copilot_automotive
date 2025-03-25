import qrcode
import base64
import socket  # 追加
from io import BytesIO
from starlette.responses import HTMLResponse
from network_utils import get_local_ip  

async def generate_qr_code(request, connected_clients):
    """Generates a QR code that directs to a connection page."""
    target_id = request.query_params.get("target_id")  # クエリパラメータから取得
    if not target_id or target_id not in connected_clients:
        return HTMLResponse("<h2>Invalid client ID</h2>", status_code=400)

    # サーバーのローカルIPアドレスを取得
    server_ip = get_local_ip()

    # QRコードに埋め込む URL
    connect_url = f"http://{server_ip}:3000/dummy_login?target_id={target_id}"

    # QRコード生成
    qr = qrcode.make(connect_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    # Base64エンコードしてHTMLで表示
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>QRコード</title>
    </head>
    <body>
        <h2>QRコードをスキャンしてください</h2>
        <img src="data:image/png;base64,{qr_base64}" alt="QR Code">
        <p>このQRコードをスキャンすると、自動的にWebSocketが接続されます。</p>
        <p>接続URL: <a href="{connect_url}">{connect_url}</a></p>
    </body>
    </html>
    """

    return HTMLResponse(html_content)