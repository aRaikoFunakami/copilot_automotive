import json
import logging
import asyncio
from typing import Dict, Any

from agent_driver_assist_ai import AgentDriverAssistAI
from dummy_data.scenario_video import scenario_data  # ダミーデータ読み込み

ENABLE_DRIVER_ASSIST = True

def is_valid_json_format(data: dict) -> bool:
    """Check if the received JSON data follows the expected format."""
    return isinstance(data, dict) and data.get("type") == "vehicle_status"

async def driver_assist_ai(ai_input_queue: asyncio.Queue, output_queue: asyncio.Queue):
    """Process valid JSON data and generate AI-based suggestions."""
    driver_assist = AgentDriverAssistAI()
    driver_assist_thread = driver_assist.create_agent()
    logging.info(f"Driver Assist AI thread created: {driver_assist_thread}")

    async def ai_generate_suggestions(data: dict) -> str:
        """Generate AI suggestions and return them as a string."""
        logging.info(f"Processing vehicle data:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        formatted_message = json.dumps(data, ensure_ascii=False)
        suggestion = await driver_assist.run_agent(formatted_message, driver_assist_thread)
        logging.info(f"AI Suggestion: {json.dumps(suggestion, ensure_ascii=False, indent=2)}")
        return suggestion if suggestion else "No suggestion generated."

    while True:
        # Retrieve data from the AI input queue
        incoming_data = await ai_input_queue.get()

        if not ENABLE_DRIVER_ASSIST:
            logging.info("Driver assist is disabled. Skipping processing.")
            continue

        if incoming_data is None:
            logging.warning("Received NoneType input. Skipping.")
            continue

        if not isinstance(incoming_data, str):
            logging.warning(f"Expected string input but got {type(incoming_data)}. Skipping.")
            continue

        # Try to parse the incoming JSON string
        try:
            parsed_data = json.loads(incoming_data)
        except json.JSONDecodeError:
            logging.warning(f"Failed to parse JSON: {incoming_data[:100]}")
            continue

        # Validate JSON structure
        if not is_valid_json_format(parsed_data):
            logging.warning(f"Invalid JSON structure: {json.dumps(parsed_data)[:100]}")
            continue

        # Generate AI suggestion
        suggestion = await ai_generate_suggestions(parsed_data)
        await output_queue.put(suggestion)
        logging.info(f"Added AI-generated suggestion to output_queue.")

#
# テスト用のコード
#
async def test_driver_assist_ai():
    """
    1) driver_assist_ai タスクを起動
    2) scenario_data の各シナリオをキューに投入
    3) 出力キューから結果を取り出して表示
    """
    ai_input_queue = asyncio.Queue()
    output_queue = asyncio.Queue()

    # Start the driver_assist_ai in the background
    driver_assist_task = asyncio.create_task(driver_assist_ai(ai_input_queue, output_queue))

    # Send each scenario from scenario_data
    for idx, scenario in enumerate(scenario_data):
        print(f"\n✅ Sending Scenario {idx+1}: {scenario['scenario']}")
        vehicle_status = {
            "type": "vehicle_status",
            "vehicle_data": scenario["vehicle_data"],
            "user_data": scenario["user_data"]
        }
        # Put the JSON string of vehicle status into the queue
        await ai_input_queue.put(json.dumps(vehicle_status, ensure_ascii=False))

        # Wait for the AI output from the output queue
        suggestion = await output_queue.get()

        # Print the result (video_proposal / schedule_proposal etc.)
        print(f"AI Output for Scenario {idx+1}:\n{json.dumps(suggestion, ensure_ascii=False, indent=2)}")

    # Cancel driver_assist_ai task after all scenarios are processed
    driver_assist_task.cancel()
    try:
        await driver_assist_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Run the test
    asyncio.run(test_driver_assist_ai())