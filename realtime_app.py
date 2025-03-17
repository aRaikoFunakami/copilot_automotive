import uvicorn
import logging
import asyncio
import json
import uuid
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from langchain_openai_voice import OpenAIVoiceReactAgent
from realtime_utils import *
from realtime_tools import TOOLS
from realtime_prompt import INSTRUCTIONS
from realtime_driver_assist_ai import driver_assist_ai
from generate_qr_code import generate_qr_code
from dummy_login import dummy_login
from network_utils import get_local_ip

# Global dictionary to manage connected clients
connected_clients = {}

# Get the local server IP address
SERVER_IP = get_local_ip()

def text_to_realtime_api_json_as_role(role: str, data_raw: str):
    data = {
        "type": "conversation.item.create",
        "item": {
            "id": "text_input",
            "type": "message",
            "role": role,
            "content": [
                {
                    "type": "input_text",
                    "text": data_raw
                }
            ],
        },
    }
    #logging.info(f"Converted text to Realtime API JSON: {data}")
    return data

async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections and manages data exchange between the client and AI."""
    try:
        await websocket.accept()
        client_id = str(uuid.uuid4())  # Generate a unique ID for this client
        logging.info(f"WebSocket connected: {client_id}")

        input_queue = asyncio.Queue()
        ai_input_queue = asyncio.Queue()

        # Store the connection
        connected_clients[client_id] = {
            "websocket": websocket,
            "input_queue": input_queue,
            "ai_input_queue": ai_input_queue
        }

        # Send client ID to the client
        await websocket.send_text(json.dumps({"type": "client_id", "client_id": client_id}))

        async def client_stream():
            """Receives data from the WebSocket client and processes messages."""
            async for message in websocket_stream(websocket):
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    message = text_to_realtime_api_json_as_role("user", message)
                    await input_queue.put(message)
                    continue
  

                if not isinstance(data, dict) or "type" not in data:
                    logging.warning("Received malformed JSON data.")
                    await websocket.send_text(json.dumps({"error": "Malformed data"}))
                    continue

                if data.get("type") == "dummy_login":
                    # Forward message to target client
                    target_id = data.get("target_id")
                    msg_content = data.get("message")

                    if target_id in connected_clients:
                        logging.info(f"Forwarding message to {target_id}: {msg_content}")
                        msg_content = text_to_realtime_api_json_as_role("user", msg_content)
                        await connected_clients[target_id]["input_queue"].put(msg_content)
                    else:
                        logging.warning(f"Target client {target_id} not found.")
                        await websocket.send_text(json.dumps({"error": "Target client not found"}))
                else:
                    # Store valid JSON messages in the input queue and ai_input_queue
                    await input_queue.put(message)
                    await ai_input_queue.put(message)

        async def merged_stream():
            """Continuously retrieves data from input_queue and sends it to the client."""
            while True:
                message = await input_queue.get()
                yield message

        agent = OpenAIVoiceReactAgent(
            model="gpt-4o-realtime-preview",
            tools=TOOLS,
            instructions=INSTRUCTIONS,
        )

        # Run AI processing in the background
        asyncio.create_task(driver_assist_ai(ai_input_queue, input_queue))

        await asyncio.gather(
            client_stream(),
            agent.aconnect(merged_stream(), websocket.send_text)
        )

    except Exception as e:
        logging.error(f"WebSocket Error: {str(e)}")
    finally:
        if client_id in connected_clients:
            del connected_clients[client_id]
        await websocket.close()
        logging.info(f"WebSocket disconnected: {client_id}")

async def generate_qr_code_with_clients(request):
    """Handles QR code generation with error handling."""
    client_id = request.query_params.get("client_id")
    if not client_id:
        return JSONResponse({"error": "Missing client_id parameter"}, status_code=400)
    return await generate_qr_code(request, connected_clients)

async def homepage(request):
    """Serves the homepage by returning the content of index.html."""
    try:
        with open("static/index.html") as f:
            html = f.read()
        return HTMLResponse(html)
    except FileNotFoundError:
        logging.error("index.html not found in static directory.")
        return HTMLResponse("<h2>Error: index.html not found</h2>", status_code=500)

async def dummy_login_with_clients(request):
    """Handles dummy login requests with error handling."""
    client_id = request.query_params.get("client_id")
    if not client_id:
        return JSONResponse({"error": "Missing client_id parameter"}, status_code=400)
    return await dummy_login(request, connected_clients)

# Define application routes
routes = [
    WebSocketRoute("/ws", websocket_endpoint),
    Route("/generate_qr", generate_qr_code_with_clients, methods=["GET"]),
    Route("/dummy_login", dummy_login_with_clients, methods=["GET"]),
    Route("/", homepage),
]

# Create Starlette application
app = Starlette(debug=True, routes=routes)

# Mount static directory
app.mount("/", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )
    uvicorn.run(app, host="0.0.0.0", port=3000)