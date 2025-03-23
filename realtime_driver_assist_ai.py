import json
import logging
import asyncio
from typing import Callable, Coroutine, Any

from agent_driver_assist_ai import AgentDriverAssistAI
from dummy_data.scenario_video import scenario_data
from dummy_data.user import user_data as dummy_user_data
from realtime_api_utils import text_to_realtime_api_json_as_role

ENABLE_DRIVER_ASSIST = True
STOP_SIGNAL = "__STOP__"  # For graceful shutdown

def is_vehicle_status(data: dict) -> bool:
    """Check if the received JSON data follows the expected format."""
    return isinstance(data, dict) and data.get("type") == "vehicle_status"

def is_user_data(data: dict) -> bool:
    """Check if the received JSON data follows the expected format."""
    return isinstance(data, dict) and data.get("type") == "user_data"

async def driver_assist_ai(
    ai_input_queue: asyncio.Queue,
    output_queue: asyncio.Queue,
    send_output_chunk: Callable[[str], Coroutine[Any, Any, None]],
    run_agent_timeout: float = 30.0
):
    """
    Process valid JSON data and generate AI-based suggestions.
    Includes:
    - Timeout for run_agent
    - Exception logging
    - Graceful stop with STOP_SIGNAL
    """
    driver_assist = AgentDriverAssistAI()
    driver_assist_thread = driver_assist.create_agent()
    logging.info(f"Driver Assist AI thread created: {driver_assist_thread}")

    # デフォルトユーザー情報を最初に読み込む
    user_lang = "ja"  # デフォルト言語（例：日本語）
    user_name = "Takeshi"  # デフォルトユーザー名
    login_user_data = dummy_user_data.get(user_name, {})  # デフォルトの user_data を取得
    previous_data = None  # 前回データ保持


    async def ai_generate_suggestions(data: dict) -> str:
        """
        Generate AI suggestions and return them as a string, with timeout & exception handling.
        """
        try:
            #logging.info(f"Processing vehicle data:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
            formatted_message = json.dumps(data, ensure_ascii=False, indent=2)
            # Timeout to prevent infinite wait if model is stuck
            suggestion = await asyncio.wait_for(
                driver_assist.run_agent(formatted_message, driver_assist_thread),
                timeout=run_agent_timeout
            )
            #logging.info(f"AI Suggestion: {json.dumps(suggestion, ensure_ascii=False, indent=2)}")
            return suggestion if suggestion else "No suggestion generated."
        except asyncio.TimeoutError:
            logging.error("run_agent timed out. Possibly stuck or unresponsive.")
            return "{}"
        except Exception as e:
            logging.error(f"Exception in ai_generate_suggestions: {e}", exc_info=True)
            return "{}"

    while True:
        try:
            incoming_data = await ai_input_queue.get()
        except Exception as e:
            logging.error(f"Exception while waiting for ai_input_queue: {e}", exc_info=True)
            continue

        # Check for stop signal
        if incoming_data == STOP_SIGNAL:
            logging.info("Stop signal received. Exiting driver_assist_ai loop.")
            break

        # 前回と同じデータならスキップ
        if incoming_data == previous_data:
            logging.info("同一データ受信のためスキップします。")
            continue
        previous_data = incoming_data

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

        if parsed_data.get("type") == "login_notice":
            user_lang = parsed_data.get("lang") or "ja"  # デフォルト言語（例：日本語）
            user_name = parsed_data.get("user_name") or "Takeshi" # default user name
            user_lookup = dummy_user_data.get(user_name)

            # エイリアス解決
            if isinstance(user_lookup, str):
                # エイリアスなら本体参照
                user_lookup = dummy_user_data.get(user_lookup)

            if isinstance(user_lookup, dict):
                login_user_data = user_lookup
                logging.info(f"User data loaded for {user_name}: {json.dumps(login_user_data, ensure_ascii=False, indent=2)}")
            else:
                logging.warning(f"User name {user_name} not found in dummy data.")
            continue

        # Validate Vehicle Status
        if not is_vehicle_status(parsed_data):
            logging.warning(f"Invalid JSON structure: {json.dumps(parsed_data)[:100]}")
            continue
        else:
            vehicle_status = parsed_data

        if "user_data" not in vehicle_status or not vehicle_status["user_data"]:
            logging.info("vehicle_status に user_data が無いため、login_user_data を補完します。")      
            if not login_user_data:
                logging.error("login_user_data が空です。補完される user_data がありません。")
            else:
                logging.info("login_user_data : %s", json.dumps(login_user_data, ensure_ascii=False, indent=2))
            vehicle_status["user_data"] = login_user_data

        # Generate AI suggestion bundle (contains multiple proposals)
        proposal_result = await ai_generate_suggestions(vehicle_status)

        # Check video_proposal layer for return_direct flag
        try:
            proposal_json = json.loads(proposal_result)          
        except json.JSONDecodeError:
            proposal_json = {}

        video_proposal = proposal_json.get("video_proposal", {})
        
        # If return_direct in video_proposal, send to client
        if isinstance(video_proposal, dict) and video_proposal.get("return_direct", False):
            logging.info("video_proposal の return_direct フラグ付きのため、クライアントに直接送信します.")
            logging.info("video_proposal : %s", json.dumps(video_proposal, ensure_ascii=False, indent=2))
            proposal_to_client = json.dumps(video_proposal, ensure_ascii=False, indent=2)
            await send_output_chunk(proposal_to_client)

            video_summary_for_ai = (
                f"I selected this video for the following reasons:\n\n"
                f"【Title】{video_proposal['title']}\n"
                f"【Genre】{video_proposal['genre']}\n"
                f"【Reason】{video_proposal['reason']}\n\n"
                f"Please explain the recommendation to the user in natural language.\n"
                f"Start your explanation by mentioning that this video was recommended because the vehicle is currently in autonomous driving mode, "
                f"which allows the user to safely enjoy video content during the ride.\n"
                f"Then, explain the other reasons for this recommendation based on the 'Reason' above, "
                f"such as matching the user's preferences (documentary, science, travel), fitting the ride time, and ensuring smooth streaming conditions.\n"
                f"Finally, briefly summarize the video content and introduce the title naturally at the end.\n"
                f"Respond in the language specified by '{user_lang}'."
            )
            await output_queue.put(text_to_realtime_api_json_as_role("user", video_summary_for_ai))
        else:
            await output_queue.put(text_to_realtime_api_json_as_role("system", proposal_result))

#
# Test code
#
async def test_driver_assist_ai():
    """
    1) Start driver_assist_ai task
    2) Put each scenario_data into the queue
    3) Retrieve and print results from output_queue
    4) Send STOP_SIGNAL and wait for normal end
    """
    ai_input_queue = asyncio.Queue()
    output_queue = asyncio.Queue()

    async def send_output_to_client(suggestion: str):
        print(f"[Client Direct Output]:\n{suggestion}")
        #await output_queue.put(suggestion)

    # Start driver_assist_ai task
    driver_assist_task = asyncio.create_task(driver_assist_ai(ai_input_queue, output_queue, send_output_to_client))

    # Send scenarios from scenario_data
    for idx, scenario in enumerate(scenario_data):
        print(f"\n[Scenario {idx + 1}] {scenario['scenario']}")
        vehicle_status = {
            "type": "vehicle_status",
            "vehicle_data": scenario["vehicle_data"],
            "user_data": scenario["user_data"]
        }
        await ai_input_queue.put(json.dumps(vehicle_status, ensure_ascii=False))

        # Retrieve AI output from the output queue
        suggestion = await output_queue.get()
        print(f"[AI Output for Scenario {idx + 1}]:\n{suggestion}")

    # All scenarios processed, now gracefully stop
    await ai_input_queue.put(STOP_SIGNAL)
    await driver_assist_task

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    asyncio.run(test_driver_assist_ai())