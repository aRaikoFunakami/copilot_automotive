# user_data_samples.py

user_data = {
    "Takeshi": {
        "user_name": "Takeshi",
        "viewer_role": "driver",
        "viewer_age": 40,
        "preferred_genres": ["documentary", "science", "travel"],
        "recent_watch_history": ["video001", "video002"]
    },
    "たけし": "Takeshi",   # alias
    "Akiko": {
        "user_name": "Akiko",
        "viewer_role": "driver",
        "viewer_age": 45,
        "preferred_genres": ["news", "sports", "action"],
        "recent_watch_history": ["video010", "video020"]
    },
    "あきこ": "Akiko",    # alias
    "Kotaro": {
        "user_name": "Kotaro",
        "viewer_role": "passenger",
        "viewer_age": 30,
        "preferred_genres": ["comedy", "drama", "anime"],
        "recent_watch_history": ["video100", "video200"]
    },
    "こたろう": "Kotaro"   # alias
}

if __name__ == "__main__":
    import json
    print(json.dumps(user_data, ensure_ascii=False, indent=2))