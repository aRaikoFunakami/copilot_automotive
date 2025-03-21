import json
import logging
import asyncio
from agent_driver_assist_ai import AgentDriverAssistAI

ENABLE_DRIVER_ASSIST = True

def is_valid_json_format(data: dict) -> bool:
    """Check if the received JSON data follows the expected format."""
    return isinstance(data, dict) and data.get("type") == "vehicle_status"

async def driver_assist_ai(ai_input_queue: asyncio.Queue, output_queue: asyncio.Queue):
    """Process valid JSON data and generate AI-based suggestions."""
    driver_assist_ai = AgentDriverAssistAI()
    driver_assist_ai_thread = driver_assist_ai.create_agent()
    logging.info(f"Driver Assist AI thread created: {driver_assist_ai_thread}")

    async def ai_generate_suggestions(data: dict) -> str:
        """Generate AI suggestions and return them as a string."""
        logging.info(f"Processing vehicle data:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        formatted_message = json.dumps(data)
        suggestion = await driver_assist_ai.run_agent(formatted_message, driver_assist_ai_thread)
        logging.info(f"AI Suggestion: {suggestion}")
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
        logging.info(f"Added AI-generated suggestion to output_queue: {suggestion}")


### TEST ###
from agent_driver_assist_ai import AgentDriverAssistAI
from dummy_data.scenario_video import scenario_data  # ダミーデータ読み込み

async def test_driver_assist_with_scenario_data():
    """
    scenario_data を読み込み、AIへ送信し、video_proposal と schedule_proposal を取得して表示
    """
    # AIエージェント初期化
    agent = AgentDriverAssistAI()
    thread_id = agent.create_agent("scenario_test_thread")

    # シナリオごとにループ
    for idx, scenario in enumerate(scenario_data):
        print(f"\n✅ Scenario {idx + 1}: {scenario['scenario']}")

        # AIに渡すvehicle_status形式に変換
        vehicle_status = {
            "type": "vehicle_status",
            "vehicle_data": scenario["vehicle_data"],
            "user_data": scenario["user_data"]
        }

        # JSON化してLangChain AIに渡す
        vehicle_status_json = json.dumps(vehicle_status, ensure_ascii=False, indent=2)

        try:
            result = await agent.run_agent(vehicle_status_json, thread_id)
        except Exception as e:
            print(f"❌ AI processing failed for Scenario {idx + 1}: {e}")
            continue

        # 出力結果確認（AIからのvideo_proposal / schedule_proposalを表示）
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # ログ出力設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # 非同期テスト実行
    asyncio.run(test_driver_assist_with_scenario_data())