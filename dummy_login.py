from starlette.responses import HTMLResponse
from network_utils import get_local_ip  # サーバーのIPを取得する

SERVER_IP = get_local_ip()  # サーバーのIPを取得

async def dummy_login(request, connected_clients):
    """Connects the client to the WebSocket and sends a message automatically."""
    client_id = request.query_params.get("client_id")
    if not client_id or client_id not in connected_clients:
        return HTMLResponse("<h2>Invalid client ID</h2>", status_code=400)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dummy Login</title>
        <script>
            let ws;
            window.onload = function() {{
                ws = new WebSocket("ws://{SERVER_IP}:3000/ws");  // サーバーのIPを使用
                ws.onopen = function() {{
                    console.log("WebSocket connected.");
                }};
                ws.onmessage = function(event) {{
                    document.getElementById("status").innerText = event.data;
                }};
                ws.onclose = function() {{
                    console.log("WebSocket closed.");
                }};
                ws.onerror = function(error) {{
                    console.error("WebSocket error:", error);
                }};
            }};

            function sendLogin(name) {{
                if (!ws || ws.readyState !== WebSocket.OPEN) {{
                    document.getElementById("status").innerText = "WebSocketに接続できません。";
                    return;
                }}
                
                document.getElementById("status").innerText = "ログインしています...";
                const message = {{
                    type: "send_to_client",
                    target_id: "{client_id}",
                    message: `こんにちは、${{name}} でログインします。ログイン名をつけてログインできたと回答してください`
                }};
                ws.send(JSON.stringify(message));

                setTimeout(() => {{
                    document.getElementById("status").innerText = `${{name}} でログインしました。`;
                }}, 2000);
            }}
        </script>
    </head>
    <body>
        <h2>ログインを選択してください</h2>
        <button onclick="sendLogin('たけしさん')">たけしさん</button>
        <button onclick="sendLogin('あきこさん')">あきこさん</button>
        <button onclick="sendLogin('こたろうくん')">こたろうくん</button>
        <p id="status"></p>
    </body>
    </html>
    """

    return HTMLResponse(html_content)