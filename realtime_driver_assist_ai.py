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
        # 現在は手動でデータがおくられてくるのでコメントアウト
        # if incoming_data == previous_data:
        #    logging.info("同一データ受信のためスキップします。")
        #    continue
        # previous_data = incoming_data

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

        await handle_proposal_json(proposal_json, user_lang, output_queue, send_output_chunk)


def select_highest_priority_proposal(proposal_json: dict, priority_table: dict) -> tuple[str, dict] | None:
    """
    Select the highest priority proposal from the given proposal_json.

    Parameters:
        proposal_json (dict): Dictionary containing multiple proposals
        priority_table (dict): Proposal type to priority number mapping (lower number = higher priority)

    Returns:
        tuple[str, dict] | None: The (proposal_key, proposal_data) with the highest priority,
                                 or None if no known proposals found
    """
    # フィルター: priority_table に定義された proposal だけを対象にする
    valid_proposals = {
        key: value for key, value in proposal_json.items()
        if key in priority_table
    }

    if not valid_proposals:
        return None  # マッチする提案がない場合

    # 優先度でソートし、一番優先度の高い（数値が小さい）ものを選択
    sorted_proposals = sorted(
        valid_proposals.items(),
        key=lambda item: priority_table[item[0]]
    )

    return sorted_proposals[0] 

async def handle_proposal_json(
    proposal_json: dict,
    user_lang: str,
    output_queue: asyncio.Queue,
    send_output_chunk: Callable[[str], Coroutine[Any, Any, None]]
):
    """
    Handle different types of proposals inside the AI response JSON.
    """
    # Select the proposal with priority
    PROPOSAL_PRIORITY = {
        "proposal_ev_charge": 1,  # 最も優先
        "proposal_video": 2,      # 優先度低め
        # 今後他の proposal が増えてもここに追加するだけで対応可能
    }

    proposal_entry = select_highest_priority_proposal(proposal_json, PROPOSAL_PRIORITY)
    if not proposal_entry:
        logging.info("有効な提案が見つかりませんでした。")
        return

    proposal_key, proposal_data = proposal_entry
    logging.info("選択された提案: %s", json.dumps(proposal_data, ensure_ascii=False, indent=2))

    # check return_direct proposals and send them directly to the client
    if proposal_data.get("return_direct", True):
        proposal_to_client = json.dumps(proposal_data, ensure_ascii=False, indent=2)
        logging.info("%s は return_direct フラグ付きのため、クライアントに直接送信します.", proposal_data["type"])
        logging.info("%s", proposal_to_client)
        await send_output_chunk(proposal_to_client)

    # special logic for each proposal type
    if "proposal_video" == proposal_key:
        logging.info("動画提案を検出しました。")
        proposal = proposal_json["proposal_video"]
        summary_for_ai = f"""
            Read the data below and briefly explain:
            1. Why is now a safe and good timing to suggest the video? (e.g., because the car is in autonomous driving mode or charging, so it’s safe to recommend content now)
            2. What kind of content is this video, and why is it a good fit for the user?
            3. How long is the video, and the duration is suitable for the user's current situation? In case of charging, the video should be within 30 minutes to fit charging time.

            # Data:
            Title: {proposal['title']}
            Genre: {proposal['genre']}
            Reason: {proposal['reason']}
            VideoDuration: {proposal['video_duration']}
            AudioOnly: {proposal['audio_only']}

            Make it sound natural, like you're recommending it because you think the timing and content are just right.
            Keep your answer concise.

            # ABSOLUTE RULE
            Respond in the language specified by '{user_lang}'. 
            """
        await output_queue.put(text_to_realtime_api_json_as_role("user", summary_for_ai))
        return


    if "proposal_ev_charge" == proposal_key:
        proposal = proposal_json["proposal_ev_charge"]
        logging.info("EV充電提案を検出しました。")
        summary_for_ai = f"""
            You are an in-vehicle AI assistant in an electric vehicle (EV).
            The following "reason" is an internal explanation for why the AI decided to suggest EV charging to the driver.
            Based on this reason, write a short, user-friendly explanation in natural language that clearly and concisely tells the user **why EV charging is being suggested right now**.

            ### Guidelines:
            - Use a casual, friendly tone (not overly formal)
            - Avoid technical jargon
            - Output should be natural language text only (no JSON, no markup)

            ### Input:
            "reason": "{{proposal['reason']}}"

            ### Example Output:
            - Your battery is running low, so it's a good time to charge. I'll show you the nearest EV charging station.
            - You might not have enough charge to reach your destination safely. I'll show you the nearest EV charging station.

            # ABSOLUTE RULE
            Respond in the language specified by '{user_lang}'.
        """
        await output_queue.put(text_to_realtime_api_json_as_role("user", summary_for_ai))
        summary_for_ai = f"""
            Repeat the following sentence exactly as it is, without adding or changing anything:
            Let me show you nearby EV charging stations.
            # ABSOLUTE RULE
            Respond in the language specified by '{user_lang}'.
        """
        await output_queue.put(text_to_realtime_api_json_as_role("user", summary_for_ai))
        return

    # その他の提案タイプがあればここで拡張可能

    # 上記に該当しない場合は proposal_json 全体を system 出力
    logging.info("既知の提案が見つからなかったため、全体を system に出力します。")
    await output_queue.put(text_to_realtime_api_json_as_role("system", json.dumps(proposal_json, ensure_ascii=False)))



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