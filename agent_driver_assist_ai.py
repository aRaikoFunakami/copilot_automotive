import asyncio
import uuid
import logging
import json
from typing import Dict

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

# グローバル管理（モード追加はここだけ）
AGENT_MODES = ["video", "schedule"]

# SYSTEM PROMPT（エスケープ済み）
SYSTEM_PROMPT = {
    "video": '''
あなたは車両内のエンターテイメントアシスタントです。
ユーザーの好みと現在の状況を考慮し、最適な動画コンテンツを提案してください。
必ず以下の形式でJSON出力してください。

以下のJSON形式で出力してください。
注意：
- "viewer_role" は "driver" または "passenger" のどちらかを必ず指定
- "driving_status" は "manual", "autonomous", "charging" のいずれか
- "network_condition" は "good" または "poor"

{{
    "proposal": {{ 
        "max_duration_sec": 1800,
        "viewer_role": "passenger",
        "viewer_age": 28,
        "preferred_genres": ["action", "comedy", "sci-fi"],
        "avoid_recently_watched": true,
        "driving_status": "autonomous",
        "network_condition": "good",
        "session_id": "abc123xyz789"
    }}
}}

''',
    "schedule": '''
あなたはスケジュール管理アシスタントです。
車両情報とカレンダー予定から遅刻の可能性を判定し、以下の形式でJSON出力してください。

{{
  "proposal": {{
    "title": "遅延通知タイトル",
    "reason": "遅延の理由",
    "action": "ユーザーへの具体的通知内容"
  }}
}}
'''
}

class AgentDriverAssistAI:
    """LangChainベースのエージェントマネージャー"""

    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.agents: Dict[str, Dict] = {}

    def create_agent(self, thread_id: str = None):
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        if thread_id not in self.agents:
            models = {mode: ChatOpenAI(model_name=self.model_name) for mode in AGENT_MODES}
            self.agents[thread_id] = {"models": models}

        return thread_id

    async def run_agent(self, user_data: str, thread_id: str):
        if thread_id not in self.agents:
            raise ValueError(f"Thread ID {thread_id} not found. Create an agent first.")

        agent_data = self.agents[thread_id]
        agent_models = agent_data["models"]

        # JSON出力保証パーサー
        parser = JsonOutputParser()

        chains = {}
        for mode in AGENT_MODES:
            prompt = PromptTemplate(
                template="{system_prompt}\n{format_instructions}\n{user_input}\n",
                input_variables=["user_input", "system_prompt"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
            )
            chains[mode] = prompt | agent_models[mode] | parser

        # 並列実行
        tasks = [
            chains[mode].ainvoke({
                "user_input": user_data,
                "system_prompt": SYSTEM_PROMPT[mode]
            }) for mode in AGENT_MODES
        ]
        results = await asyncio.gather(*tasks)

        # モードごとに結果整形
        final_response = {f"{mode}_proposal": result for mode, result in zip(AGENT_MODES, results)}

        # JSONで見やすく出力
        print(json.dumps(final_response, ensure_ascii=False, indent=2))
        return final_response

    async def run_tasks(self, messages_per_thread: Dict[str, list]):
        tasks = []
        for thread_id, messages in messages_per_thread.items():
            for message in messages:
                tasks.append(self.run_agent(message, thread_id))
        await asyncio.gather(*tasks)

# 車両ステータスサンプルデータ
'''
vehicle_status = {
    "type": "vehicle_status",
    "description": "This JSON represents the current vehicle status.",
    "speed": {"value": 60, "unit": "km/h"},
    "indoor_temperature": {"value": 20, "unit": "°C"},
    "fuel_level": {"value": 50, "unit": "%"},
    "location": {"latitude": 35.6997837, "longitude": 139.7741138},
    "address": "日本、〒101-0022 東京都千代田区神田練塀町３ 大東ビル 5階",
    "timestamp": "2025-03-17T15:27:42.781+09:00"
}
'''

from dummy_data.scenario_video import scenario_data
from agent_video_suggestion_ai import VideoRecommender

async def main():
    chat_manager = AgentDriverAssistAI()
    thread_id = chat_manager.create_agent("thread_123")

    # 車両情報をそのまま渡す
    for vehicle_status in scenario_data:
        vehicle_status_json = json.dumps(vehicle_status, ensure_ascii=False, indent=2)
        responses = await chat_manager.run_agent(vehicle_status_json, thread_id)
        recommender = VideoRecommender()
        recommended_video = await recommender.recommend(responses["video_proposal"]["proposal"])
        print("Recommended Video (JSON):")
        print(json.dumps(recommended_video, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())