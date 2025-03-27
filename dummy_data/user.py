# user_data_samples.py

user_data = {
    "Ken": {
        "user_name": "Ken",
        "viewer_role": "driver",
        "viewer_age": 40,
        "preferred_genres": ["comedy", "comedy", "comedy"],
        "recent_watch_history": ["video001", "video002"]
    },
    "けん": "Ken",   # alias
    "Yuki": {
        "user_name": "Yuki",
        "viewer_role": "driver",
        "viewer_age": 45,
        "preferred_genres": ["action", "anime", "action"],
        "recent_watch_history": ["video010", "video020"]
    },
    "ゆき": "Yuki",    # alias
    "Ryo": {
        "user_name": "Ryo",
        "viewer_role": "passenger",
        "viewer_age": 16,
        "preferred_genres": ["anime", "anime", "anime"],
        "recent_watch_history": ["video100", "video200"]
    },
    "りょう": "Ryo"   # alias
}

if __name__ == "__main__":
    import json
    print(json.dumps(user_data, ensure_ascii=False, indent=2))