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
from realtime_utils import (
    websocket_stream  # assume your existing function
)
from realtime_tools import TOOLS
from realtime_prompt import INSTRUCTIONS
from realtime_driver_assist_ai import driver_assist_ai
from generate_qr_code import generate_qr_code
from dummy_login import dummy_login_page, demo_action_page
from network_utils import get_local_ip
from page_video import page_video
from realtime_api_utils import text_to_realtime_api_json_as_role
from dummy_data.vehicle_data import vehicle_data as vehicle_data_list

# Global dictionary to manage connected clients/sessions
# Key: client_id, Value: dict with websockets, queues, agent tasks, etc.
connected_clients = {}

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


async def create_new_session(client_id: str, websocket: WebSocket):
    """
    Create a new session for this client_id with fresh queues, tasks, and agent.
    """
    logging.info(f"Creating new session for client_id: {client_id}")
    input_queue = asyncio.Queue()
    ai_input_queue = asyncio.Queue()

    # Prepare the agent
    agent = OpenAIVoiceReactAgent(
        model="gpt-4o-mini-realtime-preview",  # or "gpt-4o-realtime-preview"
        tools=TOOLS,
        instructions=INSTRUCTIONS,
    )

    # Callback to send driver assist messages back to client
    async def send_ai_output_to_client(suggestion: str):
        try:
            ws = connected_clients[client_id]["websocket"]
            # Check if WebSocket is still connected
            if ws.application_state == WebSocketState.CONNECTED:
                logging.info(f"Sending AI driver assist direct output to client {client_id}")
                await ws.send_text(suggestion)
        except Exception as e:
            logging.warning(f"Failed to send AI output: {e}")

    # Launch driver_assist_ai (continuous in background)
    driver_assist_task = asyncio.create_task(
        driver_assist_ai(ai_input_queue, input_queue, send_ai_output_to_client)
    )

    # Launch agent.aconnect in background (continuous)
    # We define a merged_stream() generator so the agent can read from input_queue
    async def merged_stream():
        while True:
            message = await input_queue.get()
            yield message

    agent_task = asyncio.create_task(
        agent.aconnect(merged_stream(), send_ai_output_to_client)
    )

    # Store session data in connected_clients
    connected_clients[client_id] = {
        "websocket": websocket,
        "input_queue": input_queue,
        "ai_input_queue": ai_input_queue,
        "agent": agent,
        "agent_task": agent_task,
        "driver_assist_task": driver_assist_task,
        "user_name": "Takeshi",  # default
        "lang": "ja",           # default
    }

    # Send client ID to the client (first time)
    await websocket.send_text(json.dumps({"type": "client_id", "client_id": client_id}))


async def reuse_session(client_id: str, websocket: WebSocket):
    """
    Reuse an existing session; simply reassign the websocket.
    """
    logging.info(f"Reusing session for client_id: {client_id}")
    connected_clients[client_id]["websocket"] = websocket

    # 通常はクライアントにID再通知するかは好み次第
    await websocket.send_text(json.dumps({"type": "client_id", "client_id": client_id}))


async def handle_websocket_messages(client_id: str, websocket: WebSocket):
    """
    Main loop that continuously receives messages from the (re)connected WebSocket.
    Puts them into the client's queues for further processing.
    """
    while True:
        try:
            # If you already have a generator function: async for msg in websocket_stream(websocket):
            # you can adapt it here. Otherwise:
            msg = await websocket.receive_text()
        except Exception as e:
            logging.warning(f"WebSocket {client_id} disconnected: {e}")
            break

        # If the WebSocket is not connected, break
        if websocket.application_state != WebSocketState.CONNECTED:
            logging.warning(f"WebSocket not connected for {client_id}, exiting message loop.")
            break

        session_data = connected_clients.get(client_id)
        if not session_data:
            # If the session is missing for some reason, break
            logging.warning(f"No session found for {client_id}, exiting message loop.")
            break

        input_queue = session_data["input_queue"]
        ai_input_queue = session_data["ai_input_queue"]

        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            # Fallback: treat as user role text
            msg_as_json = text_to_realtime_api_json_as_role("user", msg)
            await input_queue.put(msg_as_json)
            continue

        # data must be dict with "type"
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
                logging.info(f"dummy_login -> target_id:{target_id}, msg_content:{msg_content}, user_name:{user_name}, lang:{lang}")
                connected_clients[target_id]["user_name"] = user_name
                connected_clients[target_id]["lang"] = lang
                msg_login_notice = {
                    "type": "login_notice",
                    "user_name": user_name,
                    "lang": lang,
                }
                await connected_clients[target_id]["ai_input_queue"].put(json.dumps(msg_login_notice))

                logging.info(f"Forwarding login message to {target_id}: {msg_content}")
                msg_content_json = text_to_realtime_api_json_as_role("user", msg_content)
                await connected_clients[target_id]["input_queue"].put(msg_content_json)
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

                target_id_websocket = connected_clients[target_id]["websocket"]
                target_id_input_queue = connected_clients[target_id]["input_queue"]
                target_id_ai_input_queue = connected_clients[target_id]["ai_input_queue"]

                # Send the JSON to the target client to play dummy video
                await target_id_websocket.send_text(action_str)

                if action == "start_autonomous":
                    demo_mode = "Autonomous"
                elif action == "start_ev_charge":
                    demo_mode = "EV Charge"

                lang = connected_clients[target_id]["lang"]

                message = f"""
                    Please notify the user: The car is now in {demo_mode} mode.
                    Please respond in the language specified by {lang}.
                """
                logging.info(f"Forwarding demo mode to AI: {message}")
                # Also let the AI agent know to notify the user
                await target_id_input_queue.put(
                    text_to_realtime_api_json_as_role("user", message)
                )

                # Simulate wait and then send vehicle_status
                await asyncio.sleep(5)
                vehicle_data = get_vehicle_data_by_scenario(action)
                vehicle_status = {
                    "type": "vehicle_status",
                    "vehicle_data": vehicle_data,
                }
                vs_msg = json.dumps(vehicle_status, ensure_ascii=False, indent=2)
                await target_id_ai_input_queue.put(vs_msg)
                logging.info(f"Forwarding vehicle_status to AI: {vs_msg}")
            else:
                logging.warning(f"Target client {target_id} not found.")
                await websocket.send_text(json.dumps({"error": "Target client not found"}))

        elif data_type == "stop_conversation":
            logging.info(f"Received demo_action: {json.dumps(data, ensure_ascii=False, indent=2)}")
            target_id = data.get("target_id")
            if target_id in connected_clients:
                # stop playing sound at the client app
                action_str = json.dumps(data, ensure_ascii=False, indent=2)
                await connected_clients[target_id]["websocket"].send_text(action_str)
                logging.info(f"Send message to client: {action_str}")

        elif data_type == "vehicle_status":
            logging.info(f"Received vehicle_status: {json.dumps(data, ensure_ascii=False, indent=2)}")
            # Send to AI
            await ai_input_queue.put(msg)
            # Also store as system message
            sys_msg = text_to_realtime_api_json_as_role("system", json.dumps(data))
            await input_queue.put(sys_msg)
            logging.info(f"Forwarding vehicle_status to AI: {json.dumps(data, ensure_ascii=False, indent=2)}")

        else:
            # General message, store in input_queue (and/or ai_input_queue if needed)
            await input_queue.put(msg)

    # End of while True: WebSocket is disconnected
    logging.info(f"Exited message loop for client_id: {client_id}")


async def websocket_endpoint(websocket: WebSocket):
    """
    Main websocket endpoint:
    - Accepts WebSocket connection.
    - Extracts or assigns a client_id (preferably from query params).
    - If session does not exist, creates a new one; otherwise reuses it.
    - Continues reading messages until disconnect (but does NOT kill the AI session).
    """
    # Accept the WebSocket
    await websocket.accept()

    # 1) Identify the client_id
    #    例: クエリパラメータで取得 "client_id"
    client_id = websocket.query_params.get("client_id")
    if not client_id:
        # If no client_id is provided, generate a new one
        client_id = str(uuid.uuid4())
        logging.info(f"No client_id from query, generated new: {client_id}")
    else:
        logging.info(f"Incoming connection with client_id: {client_id}")

    # 2) If we don't already have a session, create a new one
    if client_id not in connected_clients:
        await create_new_session(client_id, websocket)
    else:
        # Reuse existing session
        await reuse_session(client_id, websocket)

    # 3) Start handling messages from this WebSocket
    #    (this does not block the agent tasks)
    await handle_websocket_messages(client_id, websocket)

    # 当面はセッションを削除しない：再接続を継続的に許容
    # もし最終的にクライアントを完全終了したい場合は、ここで「削除」しても良い
    # del connected_clients[client_id]
    logging.info(f"WebSocket disconnected for client_id: {client_id}")


async def generate_qr_code_with_clients(request):
    """Handles QR code generation with error handling."""
    target_id = request.query_params.get("target_id")
    if not target_id:
        return JSONResponse({"error": "Missing target_id parameter"}, status_code=400)
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
    target_id = request.query_params.get("target_id")
    if not target_id:
        return JSONResponse({"error": "Missing target_id parameter"}, status_code=400)
    
    if target_id not in connected_clients:
        return HTMLResponse("<h2>Invalid target ID</h2>", status_code=400)
    
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
    uvicorn.run(app, host="0.0.0.0", port=3000, ws_max_size=16777216)
