import json
import logging
import asyncio
from agent_driver_assist_ai import AgentDriverAssistAI

ENABLE_DRIVER_ASSIST=False

def is_valid_json_format(data: dict) -> bool:
    """Check if the received JSON data follows the expected format."""
    return (
        isinstance(data, dict)
        and data.get("type") == "conversation.item.create"
        and isinstance(data.get("item"), dict)
        and isinstance(data["item"].get("content"), list)
        and data["item"]["content"]
        and data["item"]["content"][0].get("type") == "input_text"
    )

async def driver_assist_ai(ai_input_queue: asyncio.Queue, output_queue: asyncio.Queue):
    """Process valid JSON data and generate AI-based suggestions."""
    driver_assist_ai = AgentDriverAssistAI()
    driver_assist_ai_thread = driver_assist_ai.create_agent()
    logging.info(f"driver_assist_ai thread: {driver_assist_ai_thread}")

    async def ai_generate_suggestions(data: dict) -> str:
        """Generate AI suggestions and return them as a string."""
        logging.info(f"Processing vehicle data: {json.dumps(data, indent=2)}")

        formatted_message = json.dumps(data) if isinstance(data, dict) else str(data)
        if ENABLE_DRIVER_ASSIST:
            suggestion = await driver_assist_ai.run_agent(formatted_message, driver_assist_ai_thread)
        else:
            suggestion = None
        logging.info(f"AI Suggestion: {suggestion}")

        return suggestion if suggestion else "No suggestion generated."

    while True:
        # Retrieve data from the AI input queue
        incoming_data = await ai_input_queue.get()

        if incoming_data is None:
            logging.warning("Received NoneType input. Skipping.")
            continue

        if isinstance(incoming_data, str):
            try:
                incoming_data = json.loads(incoming_data)
            except json.JSONDecodeError:
                logging.warning(f"Unexpected JSON structure: {str(incoming_data)[:100]}. Skipping.")
                continue

        if not is_valid_json_format(incoming_data):
            logging.warning(f"Unexpected JSON structure: {str(incoming_data)[:100]}. Skipping.")
            continue

        # Generate AI suggestion
        suggestion = await ai_generate_suggestions(incoming_data)
        await output_queue.put(suggestion)  # Store result in output queue
        logging.info(f"Added AI-generated suggestion to output_queue: {suggestion}")




# Test data
dummy_data = {
    "event_id": "event_1718",
    "type": "conversation.item.create",
    "previous_item_id": None,
    "item": {
        "id": "msg_003",
        "type": "message",
        "role": "user",
        "content": [
            {
                "type": "input_text",
                "text": "My name is Michael."
            }
        ]
    }
}

async def main():
    """Main function to test driver_assist_ai using dummy_data."""
    ai_input_queue = asyncio.Queue()
    output_queue = asyncio.Queue()

    # Start driver_assist_ai as an asynchronous task
    asyncio.create_task(driver_assist_ai(ai_input_queue, output_queue))

    # Ensure data is added to the queue after the AI process starts
    await asyncio.sleep(1)
    await ai_input_queue.put(dummy_data)
    logging.info("Dummy data added to ai_input_queue.")

    # Retrieve AI-generated suggestion
    suggestion = await output_queue.get()
    logging.info(f"Final AI Suggestion: {suggestion}")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")