import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser


class TrailerDB:
    def __init__(self, csv_file: str):
        self.csv_file = Path(__file__).parent / csv_file
        self.df = pd.read_csv(self.csv_file)
        self._preprocess()

    def _preprocess(self) -> None:
        self.df['duration_sec'] = self.df['video_duration'].apply(self._time_to_seconds)

    @staticmethod
    def _time_to_seconds(time_str: str) -> int:
        if pd.isna(time_str):
            return 0
        parts = list(map(int, time_str.split(":")))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return 0

    def get_video_candidates(self, max_duration_sec: int) -> List[Dict[str, Any]]:
        filtered = self.df[self.df['duration_sec'] <= max_duration_sec]
        return filtered[['title', 'genre', 'iframe']].to_dict(orient='records')


def build_user_prompt(proposal: Dict[str, Any], candidates: List[Dict[str, Any]]) -> str:
    return f"""
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
- Preferred genres: {', '.join(proposal['preferred_genres'])}

Candidate Videos:
{json.dumps(candidates, ensure_ascii=False, indent=2)}

If a video is suitable, output in this JSON format:
{{
  "no_suitable_video": false,
  "title": "<video_title>",
  "genre": "<video_genre>",
  "iframe": "<video_iframe>",
  "reason": "<why you chose this video>"
}}

If no suitable video is found, output exactly this JSON and explain the reason:
{{
  "no_suitable_video": true,
  "title": "",
  "genre": "",
  "iframe": "",
  "reason": "<explain clearly why no candidate was suitable>"
}}

IMPORTANT:
- Output ONLY pure JSON. DO NOT use ```json or any markdown.
- reason shall be in Japanese
"""


class VideoRecommender:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1
        )
        self.parser = JsonOutputParser()

    async def recommend(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        #response = await self.llm.ainvoke(messages)
        #return self.parser.parse(response.content)
        chain = self.llm | self.parser
        response = await chain.ainvoke(messages)
        return response


async def main():
    db = TrailerDB('dummy_data/trailer_db.csv')

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

    candidates = db.get_video_candidates(proposal['max_duration_sec'])

    system_prompt = "You are a helpful AI video recommender."
    user_prompt = build_user_prompt(proposal, candidates)

    recommender = VideoRecommender()
    recommended_video = await recommender.recommend(system_prompt, user_prompt)

    print("Recommended Video (JSON):")
    print(json.dumps(recommended_video, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())