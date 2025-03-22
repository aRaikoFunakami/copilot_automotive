from starlette.responses import FileResponse, HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket
import uvicorn
from pathlib import Path

connected_clients = set()

# HTML表示エンドポイント
async def dummy_login_page(request):
    html_path = Path(__file__).parent / "static" / "dummy_login.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h2>Template not found.</h2>", status_code=404)

### TEST ###

# WebSocketエンドポイント
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print("WebSocket Connected")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"📨 Received: {data}")
            # 受け取った内容をそのまま全クライアントにブロードキャスト
            for client in connected_clients:
                await client.send_text(f"Echo: {data}")
    except Exception as e:
        print(f"❌ WebSocket Error: {e}")
    finally:
        connected_clients.remove(websocket)
        await websocket.close()
        print("🚪 WebSocket Disconnected")

# ルーティング
app = Starlette(debug=True, routes=[
    Route("/dummy_login", dummy_login_page),
    WebSocketRoute("/ws", websocket_endpoint),  # WebSocket対応
])

if __name__ == "__main__":
    print("🌐 Server running: http://localhost:3000/dummy_login?client_id=test1234")
    print("🛰 WebSocket endpoint: ws://localhost:3000/ws")
    uvicorn.run(app, host="0.0.0.0", port=3000)