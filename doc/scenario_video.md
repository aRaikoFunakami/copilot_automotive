## 動画提案のタイミング（まとめ）

| パターン                          | 残り走行時間    | 運転状況      | 視聴者     | コメント                                   |
|-----------------------------------|----------------|-------------|----------|--------------------------------------------|
| 1. 自動運転中のドライバー提案     | 1200秒（20分） | 自動運転     | ドライバー | 高速道路自動運転中、提案OK                 |
| 2. EV充電中のドライバー提案       | 1500秒（25分） | 充電中       | ドライバー | 停車中、安心して提案可能                   |
| 3. 走行中の同乗者提案             | 900秒（15分）  | 手動運転中   | 同乗者     | 走行中でも同乗者向けなら提案OK             |

```json
[
    {
      "scenario": "自動運転中のドライバーへの提案",
      "vehicle_data": {
        "current_location": { "lat": 35.6895, "lon": 139.6917 },
        "destination_info": { "distance_km": 30.0, "eta_sec": 1200 },
        "driving_status": "autonomous",
        "network_status": "good",
        "vehicle_speed": 100,
        "energy_status": { "battery_level": 70, "charging": false }
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
        "current_location": { "lat": 34.6937, "lon": 135.5023 },
        "destination_info": { "distance_km": 20.0, "eta_sec": 1500 },
        "driving_status": "charging",
        "network_status": "good",
        "vehicle_speed": 0,
        "energy_status": { "battery_level": 35, "charging": true }
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
        "current_location": { "lat": 35.0116, "lon": 135.7681 },
        "destination_info": { "distance_km": 15.0, "eta_sec": 900 },
        "driving_status": "manual",
        "network_status": "good",
        "vehicle_speed": 60,
        "energy_status": { "battery_level": 60, "charging": false }
      },
      "user_data": {
        "viewer_role": "passenger",
        "viewer_age": 30,
        "preferred_genres": ["comedy", "drama", "anime"],
        "recent_watch_history": ["video100", "video200"]
      }
    }
  ]
  ```