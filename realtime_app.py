import uvicorn
import logging
import asyncio
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from langchain_openai_voice import OpenAIVoiceReactAgent
from realtime_utils import *
from realtime_tools import TOOLS
from realtime_prompt import INSTRUCTIONS
from realtime_driver_assist_ai import driver_assist_ai

async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections and manages data exchange between the client and AI."""
    try:
        await websocket.accept()
        logging.info("WebSocket connection accepted.")

        input_queue = asyncio.Queue()  # Queue to store data from the WebSocket client and AI results
        ai_input_queue = asyncio.Queue()  # Dedicated queue for sending data to AI

        async def client_stream():
            """Receives data from the WebSocket client and sends it to input_queue and ai_input_queue."""
            async for message in websocket_stream(websocket):
                await input_queue.put(message)  # Send WebSocket data to input_queue
                await ai_input_queue.put(message)  # Send the same data to AI

        async def merged_stream():
            """Continuously retrieves data from input_queue and sends it to the WebSocket client."""
            while True:
                message = await input_queue.get()  # Retrieve messages, including AI results
                yield message  # Send message to WebSocket client

        agent = OpenAIVoiceReactAgent(
            model="gpt-4o-realtime-preview",
            tools=TOOLS,
            instructions=INSTRUCTIONS,
        )

        # Run `driver_assist_ai(ai_input_queue, input_queue)` in the background
        asyncio.create_task(driver_assist_ai(ai_input_queue, input_queue))

        await asyncio.gather(
            client_stream(),
            agent.aconnect(merged_stream(), websocket.send_text)
        )

    except Exception as e:
        logging.error(f"WebSocket Error: {str(e)}")

    finally:
        await websocket.close()
        logging.info("WebSocket connection closed.")

async def homepage(request):
    """Serves the homepage by returning the content of index.html."""
    with open("static/index.html") as f:
        html = f.read()
        return HTMLResponse(html)

# Define application routes
routes = [
    WebSocketRoute("/ws", websocket_endpoint),  # WebSocket route
    Route("/", homepage),  # Homepage route
]

# Create Starlette application
app = Starlette(debug=True, routes=routes)

# Mount the static files directory
app.mount("/", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # Configure logging format
    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )
    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=3000)