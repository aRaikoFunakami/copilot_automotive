import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import os

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
    

if __name__ == "__main__":
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

    db = TrailerDB('trailer_db.csv')
    candidates = db.get_video_candidates(proposal['max_duration_sec'])
    print(json.dumps(candidates, ensure_ascii=False, indent=2))