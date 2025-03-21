"""
Response JSON Format Specification:

{
    "has_recommendation": bool,    # True if a recommended video is found, False otherwise
    "title": str,                  # Title of the recommended video (empty if no recommendation)
    "genre": str,                  # Genre of the recommended video (empty if no recommendation)
    "iframe": str,                 # Embeddable iframe HTML (empty if no recommendation)
    "reason": str,                 # Reason for recommendation or explanation in Japanese
    "data_broken": bool            # True if input data is invalid or corrupted, False otherwise
}
"""

import logging
from pathlib import Path
import pandas as pd
import json
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate
from dummy_data.trailer_db import TrailerDB

user_prompt_template = """
You are an AI video recommender.

Choose ONE video ONLY from the candidate list below. Follow the rules:

Rules:
- DO NOT invent videos. Recommend ONLY from the candidate list.
- All videos are pre-filtered by max_duration. No need to check duration.
- Prioritize videos matching the user's preferred genres.
- If no exact match, you MAY select a video from a similar or related genre.
- If you cannot find any suitable video, explain clearly WHY in the reason field.

Genre matching rules (examples of similarity you should consider):
- "science" may include "education"
- "documentary" may include "education" or "news"
- "travel" may include "documentary", "culture", or "history"

User preferences:
- Preferred genres: {preferred_genres}

Candidate Videos:
{candidates}

Respond ONLY in the following pure JSON format:

If a suitable video is found:
{{
  "has_recommendation": true,
  "title": "<video_title>",
  "genre": "<video_genre>",
  "iframe": "<video_iframe>",
  "reason": "<why you chose this video>"
}}

If no suitable video is found:
{{
  "has_recommendation": false,
  "title": "",
  "genre": "",
  "iframe": "",
  "reason": "<explain clearly why no candidate was suitable>"
}}

IMPORTANT:
- Output ONLY pure JSON. DO NOT use ```json or any markdown.
- reason must be written in Japanese
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
            input_variables=["preferred_genres", "candidates"]
        )

    async def recommend(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        required_keys = ["max_duration_sec", "preferred_genres"]
        if not isinstance(proposal, dict) or not all(key in proposal for key in required_keys):
            logging.error(f"[VideoRecommender] Invalid proposal data: {proposal}")
            return {
                "has_recommendation": False,
                "title": "",
                "genre": "",
                "iframe": "",
                "reason": "入力データが不正または不足しています（データ破損の可能性あり）",
                "data_broken": True
            }

        candidates = self.db.get_video_candidates(proposal['max_duration_sec'])
        user_prompt = self.prompt_template.format(
            preferred_genres=", ".join(proposal["preferred_genres"]),
            candidates=json.dumps(candidates, ensure_ascii=False, indent=2)
        )

        system_prompt = "You are a helpful AI video recommender."
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        chain = self.llm | self.parser
        response = await chain.ainvoke(messages)

        response["data_broken"] = False
        return response


async def main():
    proposal = {
        "max_duration_sec": 1800,
        "viewer_role": "driver",
        "viewer_age": 40,
        "preferred_genres": ["documentary", "science", "travel"],
        "avoid_recently_watched": True,
        "driving_status": "autonomous",
        "network_condition": "good",
        "session_id": "xyz123abc456"
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