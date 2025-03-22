from starlette.responses import FileResponse, HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket
import uvicorn
from pathlib import Path
from starlette.staticfiles import StaticFiles

connected_clients = set()
BASE_DIR = Path(__file__).parent

# /dummy_login 
async def dummy_login_page(request):
    html_path = BASE_DIR / "static" / "dummy_login.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h2>Template not found.</h2>", status_code=404)

# /demo_action/{action} 
async def demo_action_page(request):
    html_path = BASE_DIR / "static" / "demo" / "demo_template.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h2>Demo page not found.</h2>", status_code=404)


### TEST ###

# WebSocket 
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print("WebSocket Connected")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received: {data}")
            # Broadcast to all connected clients
            for client in connected_clients:
                await client.send_text(f"Echo: {data}")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        connected_clients.remove(websocket)
        await websocket.close()
        print("WebSocket Disconnected")

# ルーティング設定
app = Starlette(debug=True, routes=[
    Route("/dummy_login", dummy_login_page),
    Route("/demo_action/{action}", demo_action_page),
    WebSocketRoute("/ws", websocket_endpoint),
])

# 静的ファイルの配信設定を追加
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    print("Server running: http://localhost:3000/dummy_login?client_id=test1234")
    print("WebSocket endpoint: ws://localhost:3000/ws")
    print("Demo Page: http://localhost:3000/demo_action/start_autonomous")
    print("Demo Page: http://localhost:3000/demo_action/start_ev_charge")
    uvicorn.run(app, host="0.0.0.0", port=3000)