"""
Response JSON Format Specification:

{
    "has_recommendation": bool,    # True if a recommended video is found, False otherwise
    "title": str,                  # Title of the recommended video (empty if no recommendation)
    "genre": str,                  # Genre of the recommended video (empty if no recommendation)
    "iframe": str,                 # Embeddable iframe HTML (empty if no recommendation)
    "reason": str,                 # Reason for recommendation or explanation in English
    "data_broken": bool,           # True if input data is invalid or corrupted, False otherwise
    "video_url": str               # URL to access the video page
}
"""

import logging
from pathlib import Path
import pandas as pd
import json
from typing import List, Dict, Any
import urllib.parse

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate
from dummy_data.trailer_db import TrailerDB
from network_utils import get_local_ip

user_prompt_template = """
You are an AI video recommender.

Choose ONE video ONLY from the candidate list below.

Rules:
- DO NOT invent videos. Recommend ONLY from the candidate list.
- The candidate list has already been pre-filtered by relevance, duration, and genre.
- Select the video that best matches the user's interests based on the available options.
- If no suitable video is found, explain clearly why in the reason field.

User Proposal (input data):
{proposal}


Candidate Videos:
{candidates}

Respond ONLY in the following pure JSON format:

If a suitable video is found:
{{
  "has_recommendation": true,
  "title": "<video_title (must match exactly)>",
  "genre": "<video_genre>",
  "iframe": "<video_iframe (copy from candidate)>",
  "reason": "<brief explanation of why this video was selected>"
  "video_duration" : "<video duration>",
  "audio_only": "<video with audio or audio only content>",
}}

If no suitable video is found:
{{
  "has_recommendation": false,
  "title": "",
  "genre": "",
  "iframe": "",
  "reason": "<explanation of why no video was selected>"
}}

IMPORTANT:
- Output ONLY pure JSON. DO NOT use ```json or any markdown.
- You MUST select from the candidate list exactly as provided.
- reason must be written in English.
"""



class VideoRecommender:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1
        ).bind(
            response_format={"type": "json_object"}
        )
        self.parser = JsonOutputParser()

        base_dir = Path(__file__).parent
        db_path = base_dir / 'dummy_data' / 'trailer_db.csv'
        self.db = TrailerDB(str(db_path))

        self.prompt_template = PromptTemplate(
            template=user_prompt_template,
            input_variables=["proposal", "candidates"]
        )

        # 動的にローカルIP取得（初期化時に取得）
        self.server_ip = get_local_ip()

    async def recommend(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        required_keys = ["max_duration_sec", "preferred_genres"]
        if not isinstance(proposal, dict) or not all(key in proposal for key in required_keys):
            logging.error(f"[VideoRecommender] Invalid proposal data: {proposal}")
            return {
                "has_recommendation": False,
                "title": "",
                "genre": "",
                "iframe": "",
                "video_duration" : "",
                "audio_only": "",
                "reason": "入力データが不正または不足しています（データ破損の可能性あり）",
                "data_broken": True,
                "video_url": ""
            }

        candidates = self.db.get_video_candidates(proposal)

        logging.info(json.dumps(proposal, ensure_ascii=False, indent=2))
        logging.info(json.dumps(candidates, ensure_ascii=False, indent=2))
        
        user_prompt = self.prompt_template.format(
            proposal=json.dumps(proposal, ensure_ascii=False, indent=2),
            candidates=json.dumps(candidates, ensure_ascii=False, indent=2)
        )

        system_prompt = "You are a helpful AI video recommender."
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        chain = self.llm | self.parser
        response = await chain.ainvoke(messages)

        # フラグ追加
        response["data_broken"] = False

        # 成功時のみ video_url を追加
        if response.get("has_recommendation"):
            encoded_title = urllib.parse.quote(response["title"])
            response["video_url"] = f"http://{self.server_ip}:3000/videos/{encoded_title}"
            response["reason"] = proposal.get("reason", "特に指定はありません。") + response["reason"] 
        else:
            response["video_url"] = ""

        return response


async def main():
    proposal = {
        "max_duration_sec": 1800,
        "viewer_role": "driver",
        "viewer_age": 40,
        "preferred_genres": ["コメディー"],
        "avoid_recently_watched": True,
        "driving_status": "autonomous",
        "network_condition": "good",
        "session_id": "xyz123abc456",
        "reason": "The vehicle is currently charging, and the battery level is at 35%. The estimated time of arrival (ETA) to your destination is 25 minutes once charging is complete.",
    }

    error_proposal = {}

    recommender = VideoRecommender()

    recommended_video = await recommender.recommend(proposal)
    print("Recommended Video (正常ケース):")
    print(json.dumps(recommended_video, ensure_ascii=False, indent=2))

    recommended_video = await recommender.recommend(error_proposal)
    print("\nError Case (データ破損時):")
    print(json.dumps(recommended_video, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import asyncio
    asyncio.run(main())