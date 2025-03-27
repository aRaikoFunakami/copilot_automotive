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

    def get_video_candidates(self, proposal: Dict[str, Any]) -> List[Dict[str, Any]]:
        max_duration_sec = proposal.get("max_duration_sec", 1800)
        driving_status = proposal.get("driving_status", "autonomous")

        # Step 1: Filter by max_duration_sec
        filtered = self.df[self.df['duration_sec'] <= max_duration_sec]

        # Step 2: Sort and group depending on driving_status
        if driving_status == "charging":
            # Additional constraint: within 30 minutes (1800 seconds), and shortest video per genre
            filtered = filtered[filtered['duration_sec'] <= 1800]
            per_genre = (
                filtered.sort_values('duration_sec', ascending=True)
                        .groupby('genre', as_index=False)
                        .first()
            )
        else:
            # Default: longest video per genre
            per_genre = (
                filtered.sort_values('duration_sec', ascending=False)
                        .groupby('genre', as_index=False)
                        .first()
            )

        return per_genre[['title', 'genre', 'iframe']].to_dict(orient='records')


    

if __name__ == "__main__":
    proposal = {
        "max_duration_sec": 11800,
        "viewer_role": "driver",
        "viewer_age": 40,
        "preferred_genres": ["documentary", "science", "travel"],
        "avoid_recently_watched": True,
        "driving_status": "autonomous",
        "network_condition": "good",
        "session_id": "xyz123abc456"
    }

    db = TrailerDB('trailer_db.csv')
    candidates = db.get_video_candidates(proposal)
    print("autonomous")
    print(json.dumps(candidates, ensure_ascii=False, indent=2))

    proposal["driving_status"] = "charging"
    candidates = db.get_video_candidates(proposal)
    print("charging")
    print(json.dumps(candidates, ensure_ascii=False, indent=2))