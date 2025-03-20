# Sample scenario data loaded as Python data (list of dictionaries)

scenario_data = [
    {
        "scenario": "自動運転中のドライバーへの提案",
        "vehicle_data": {
            "current_location": {"lat": 35.6895, "lon": 139.6917},
            "destination_info": {"distance_km": 30.0, "eta_sec": 1200},
            "driving_status": "autonomous",
            "network_status": "good",
            "vehicle_speed": 100,
            "energy_status": {"battery_level": 70, "charging": False}
        },
        "user_data": {
            "viewer_role": "driver",
            "viewer_age": 40,
            "preferred_genres": ["documentary", "science", "travel"],
            "recent_watch_history": ["video001", "video002"]
        }
    },
    {
        "scenario": "EV充電中のドライバーへの提案",
        "vehicle_data": {
            "current_location": {"lat": 34.6937, "lon": 135.5023},
            "destination_info": {"distance_km": 20.0, "eta_sec": 1500},
            "driving_status": "charging",
            "network_status": "good",
            "vehicle_speed": 0,
            "energy_status": {"battery_level": 35, "charging": True}
        },
        "user_data": {
            "viewer_role": "driver",
            "viewer_age": 45,
            "preferred_genres": ["news", "sports", "action"],
            "recent_watch_history": ["video010", "video020"]
        }
    },
    {
        "scenario": "走行中の同乗者への提案",
        "vehicle_data": {
            "current_location": {"lat": 35.0116, "lon": 135.7681},
            "destination_info": {"distance_km": 15.0, "eta_sec": 900},
            "driving_status": "manual",
            "network_status": "good",
            "vehicle_speed": 60,
            "energy_status": {"battery_level": 60, "charging": False}
        },
        "user_data": {
            "viewer_role": "passenger",
            "viewer_age": 30,
            "preferred_genres": ["comedy", "drama", "anime"],
            "recent_watch_history": ["video100", "video200"]
        }
    }
]