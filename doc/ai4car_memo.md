# 動画検索インターフェース仕様書

## 1. 必要入力データ仕様（車両データ / 個人データ）

### 車両データ（Vehicle Data）

| パラメータ | 型 | 必須 | 説明 |
|-----------|----|------|------|
| current_location | object `{lat: float, lon: float}` | 必須 | 現在のGPS位置 |
| destination_info | object `{distance_km: float, eta_sec: int}` | 必須 | 目的地までの距離・残り秒数 |
| driving_status | enum(`manual`, `autonomous`, `charging`) | 必須 | 現在の運転状況 |
| network_status | enum(`good`, `poor`) | 必須 | 通信状況 |
| vehicle_speed | float | 任意 | 現在の速度（km/h） |
| energy_status | object `{battery_level: int, charging: bool}` | 任意 | バッテリー情報（EVのみ） |

### 個人データ（User / Passenger Data）

| パラメータ | 型 | 必須 | 説明 |
|-----------|----|------|------|
| viewer_role | enum(`driver`, `passenger`) | 必須 | 視聴者の役割 |
| viewer_age | int | 必須 | 年齢（年齢制限判定用） |
| preferred_genres | list(string) | 必須 | 好みのジャンル |
| recent_watch_history | list(video_id) | 必須 | 直近視聴履歴（重複排除用） |
| user_id | string | 任意 | ユーザー識別ID（パーソナライズ強化用） |

---

### 【追加】入力データ JSON仕様（車両・個人まとめ）

```json
{
  "vehicle_data": {
    "current_location": { "lat": 35.6895, "lon": 139.6917 },
    "destination_info": { "distance_km": 30.5, "eta_sec": 1800 },
    "driving_status": "autonomous",
    "network_status": "good",
    "vehicle_speed": 80,
    "energy_status": { "battery_level": 80, "charging": false }
  },
  "user_data": {
    "viewer_role": "driver",
    "viewer_age": 35,
    "preferred_genres": ["action", "sci-fi", "comedy"],
    "recent_watch_history": ["video123", "video456"],
    "user_id": "user-abc-123"
  }
}
```

## 2. 外部動画検索エンジンへの送信データ仕様（出力データ）

### 出力データ項目定義

| パラメータ              | 型                       | 必須 | 説明                                       |
|-------------------------|--------------------------|------|--------------------------------------------|
| max_duration_sec        | int                      | 必須 | 視聴可能な最大再生時間（秒）               |
| viewer_role             | enum(`driver`, `passenger`) | 必須 | 視聴者の役割（運転者 or 同乗者）           |
| viewer_age              | int                      | 必須 | 視聴者の年齢（年齢制限考慮）               |
| preferred_genres        | list(string)             | 必須 | 視聴者の好みジャンル                       |
| avoid_recently_watched  | boolean                  | 必須 | 直近視聴済みコンテンツを除外するか         |
| driving_status          | enum(`manual`, `autonomous`, `charging`) | 必須 | 現在の運転状況                             |
| network_condition       | enum(`good`, `poor`)     | 必須 | 通信状況（ネットワーク環境）               |
| session_id              | string                   | 必須 | 一意なセッションID（リクエスト追跡用）     |

---

### 外部動画検索エンジンへの送信JSON仕様（例）

```json
{
  "max_duration_sec": 1800,
  "viewer_role": "driver",
  "viewer_age": 35,
  "preferred_genres": ["action", "documentary", "animation"],
  "avoid_recently_watched": true,
  "driving_status": "autonomous",
  "network_condition": "good",
  "session_id": "abcde-12345-67890-fghij"
}
```