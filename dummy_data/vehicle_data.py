vehicle_data = [
    {
        "scenario": "自動運転中のドライバーへの提案",
        "vehicle_data": {
            "current_location": {"lat": 35.6895, "lon": 139.6917},
            "destination_info": {"distance_km": 30.0, "eta_sec": 1200},
            "driving_status": "autonomous",
            "network_status": "good",
            "vehicle_speed": 100,
            "energy_status": {"battery_level": 70, "charging": False}
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
        }
    }
]