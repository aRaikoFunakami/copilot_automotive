## 遅刻検出・対応判断のための入力データ例（3パターン）

### 1. 渋滞で予定に遅れそうなケース

```json
{
  "current_time": "2025-03-18T08:00:00+09:00",
  "estimated_arrival_time": "2025-03-18T08:45:00+09:00",
  "calendar_event": {
    "event_title": "取引先訪問",
    "start_time": "2025-03-18T08:30:00+09:00",
    "location": "東京都港区"
  },
  "traffic_condition": "heavy"
}
```

## 2. EV充電が必要で間に合わないケース

```json
{
  "current_time": "2025-03-18T13:00:00+09:00",
  "estimated_arrival_time": "2025-03-18T14:10:00+09:00",
  "calendar_event": {
    "event_title": "オンライン会議",
    "start_time": "2025-03-18T14:00:00+09:00",
    "location": "自宅"
  },
  "battery_level": 15,
  "charging_required": true
}
```

## 3. 途中で子どもを送る予定が入り間に合わないケース

```json
{
  "current_time": "2025-03-18T15:00:00+09:00",
  "estimated_arrival_time": "2025-03-18T16:10:00+09:00",
  "calendar_event": {
    "event_title": "病院予約",
    "start_time": "2025-03-18T16:00:00+09:00",
    "location": "市民病院"
  },
  "unexpected_task": {
    "task": "子どもの送り",
    "estimated_task_time": "2025-03-18T15:20:00+09:00",
    "task_duration_min": 30
  }
}
```