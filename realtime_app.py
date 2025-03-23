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
from starlette.websockets import WebSocketState

from langchain_openai_voice import OpenAIVoiceReactAgent
from realtime_utils import *
from realtime_tools import TOOLS
from realtime_prompt import INSTRUCTIONS
from realtime_driver_assist_ai import driver_assist_ai
from generate_qr_code import generate_qr_code
from dummy_login import dummy_login_page, demo_action_page
from network_utils import get_local_ip
from page_video import page_video
from realtime_api_utils import text_to_realtime_api_json_as_role
from dummy_data.vehicle_data import vehicle_data as vehicle_data_list

# Global dictionary to manage connected clients
connected_clients = {}

# Get the local server IP address
SERVER_IP = get_local_ip()

def get_vehicle_data_by_scenario(action):
    """
    Extract vehicle_data from the list by matching the scenario.
    """
    for item in vehicle_data_list:
        if item["action"] == action:
            logging.error(f"Scenario : %s", json.dumps(item["vehicle_data"], ensure_ascii=False, indent=2))
            print(item["vehicle_data"])
            return item["vehicle_data"]
        
    logging.error(f"Scenario not found: {action}")
    return None


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
            "ai_input_queue": ai_input_queue,
            # デフォルトユーザー情報をセット
            "user_name": "Takeshi",
            "lang": "ja"
        }

        # Send client ID to the client
        await websocket.send_text(json.dumps({"type": "client_id", "client_id": client_id}))

        async def client_stream():
            """Receives data from the WebSocket client and processes messages."""
            try:
                async for message in websocket_stream(websocket):
                    logging.info(f"Received message: {message}")
                    try:
                        logging.info(f"try json load: {message}")
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        message = text_to_realtime_api_json_as_role("user", message)
                        await input_queue.put(message)
                        continue
    
                    logging.info(f"Received data: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    if not isinstance(data, dict) or "type" not in data:
                        logging.warning("Received malformed JSON data.")
                        await websocket.send_text(json.dumps({"error": "Malformed data"}))
                        continue

                    data_type = data.get("type")
                    logging.info(f"Received data_type: {data_type}")

                    if data_type == "dummy_login":
                        logging.info(f"Received dummy_login: {json.dumps(data, ensure_ascii=False, indent=2)}")
                        # Forward message to target client
                        target_id = data.get("target_id")
                        msg_content = data.get("message")
                        user_name = data.get("user_name")
                        lang = data.get("lang")

                        if target_id in connected_clients:
                            logging.info(f"Received message: target_id:{target_id}, mas_content:{msg_content}, user_name:{user_name}, lang:{lang}")
                            connected_clients[target_id]["user_name"] = user_name
                            connected_clients[target_id]["lang"] = lang
                            msg_login_notice = {
                                "type": "login_notice",
                                "user_name": user_name,
                                "lang": lang,
                            }
                            await connected_clients[target_id]["ai_input_queue"].put(json.dumps(msg_login_notice))

                            logging.info(f"Forwarding message to {target_id}: {msg_content} ")
                            msg_content = text_to_realtime_api_json_as_role("user", msg_content)
                            await connected_clients[target_id]["input_queue"].put(msg_content)
                        else:
                            logging.warning(f"Target client {target_id} not found.")
                            await websocket.send_text(json.dumps({"error": "Target client not found"}))
                    elif data_type == "demo_action":
                        logging.info(f"Received demo_action: {json.dumps(data, ensure_ascii=False, indent=2)}")
                        target_id = data.get("target_id")
                        if target_id in connected_clients:
                            action = data.get("action")
                            server_ip = get_local_ip()
                            video_url = f"http://{server_ip}:3000/demo_action/{action}"
                            data["video_url"] = video_url

                            action_str = json.dumps(data, ensure_ascii=False, indent=2)
                            logging.info(f"Send message to client: {action_str}")

                            # クライアント側でダミー動画を再生する
                            target_id_websocket = connected_clients[target_id]["websocket"]
                            #target_id_input_queue = connected_clients[target_id]["input_queue"]
                            target_id_ai_input_queue = connected_clients[target_id]["ai_input_queue"]
                            await target_id_websocket.send_text(action_str)

                            # AIにダミーのvehicle_statusを渡す
                            vehicle_data = get_vehicle_data_by_scenario(action)

                            # user_data は AI側がユーザーを知っているので自動追加される
                            vehicle_status = {
                                "type": "vehicle_status",
                                "vehicle_data": vehicle_data,
                            }
                            message = json.dumps(vehicle_status, ensure_ascii=False, indent=2)
                            await target_id_ai_input_queue.put(message)
                            logging.info(f"Forwarding vehicle_status to AI: {json.dumps(vehicle_status, ensure_ascii=False, indent=2)}")
                        else:
                            logging.warning(f"Target client {target_id} not found.")
                            await websocket.send_text(json.dumps({"error": "Target client not found"}))
                    elif data_type == "vehicle_status":
                        logging.info(f"Received vehicle_status: {json.dumps(data, ensure_ascii=False, indent=2)}")
                        await ai_input_queue.put(message)
                        await input_queue.put(text_to_realtime_api_json_as_role("system", json.dumps(data))) # str to dumps あとで確認する
                        logging.info(f"Forwarding vehicle_status to AI: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    else:
                        # Store valid JSON messages in the input queue and ai_input_queue
                        await input_queue.put(message)
            except Exception as e:
                logging.error(f"WebSocket receive error: {e}, client_id: {client_id}")
                raise
                        

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

        # driver_assist_aiへのコールバック渡し（リアルタイム送信用）
        async def send_ai_output_to_client(suggestion: str):
            logging.info(f"Sending AI driver assist direct output to client {client_id}")
            await websocket.send_text(suggestion)

        # AIドライバーアシスト起動（send_output_chunk対応）
        asyncio.create_task(driver_assist_ai(ai_input_queue, input_queue, send_ai_output_to_client))


        await asyncio.gather(
            client_stream(),
            agent.aconnect(merged_stream(), websocket.send_text)
        )

    except Exception as e:
        logging.error(f"WebSocket Error: {str(e)}")
    finally:
        if client_id in connected_clients:
            del connected_clients[client_id]

        try:
            if websocket.application_state != WebSocketState.DISCONNECTED:
                await websocket.close()
        except Exception as e:
            logging.warning(f"Error while closing WebSocket: {str(e)}")
        
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
    
    if not client_id or client_id not in connected_clients:
        return HTMLResponse("<h2>Invalid client ID</h2>", status_code=400)
    
    return await dummy_login_page(request)

# Define application routes
routes = [
    WebSocketRoute("/ws", websocket_endpoint),
    Route("/generate_qr", generate_qr_code_with_clients, methods=["GET"]),
    Route("/dummy_login", dummy_login_with_clients, methods=["GET"]),
    Route("/demo_action/{action}", demo_action_page),
    Route("/videos/{title}", page_video, methods=["GET"]),
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