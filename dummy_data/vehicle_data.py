vehicle_data = [
    {
        "scenario": "自動運転中のドライバーへの提案",
        "action": "start_autonomous",
        "vehicle_data": {
            "current_location": {"lat": 35.6895, "lon": 139.6917},
            "destination_info": {"distance_km": 160.0, "eta_sec": 8200},
            "driving_status": "autonomous",
            "network_status": "good",
            "vehicle_speed": 100,
            "energy_status": {"battery_level": 70, "charging": False}
        }
    },
    {
        "scenario": "EV充電中のドライバーへの提案",
        "action": "start_ev_charge",
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
        "scenario": "EV充電中のドライバーへの提案（バッテリー残量低下）",
        "action": "start_battery_level_low",
        "vehicle_data": {
            "current_location": {"lat": 35.6895, "lon": 139.6917},
            "destination_info": {"distance_km": 50.0, "eta_sec": 3600},
            "driving_status": "manual",
            "network_status": "good",
            "vehicle_speed": 50,
            "energy_status": {"battery_level": 15, "charging": False}
        }
    }
]