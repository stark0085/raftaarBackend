# MasterApi - Raftaar Dashboard Backend

This backend powers the railway dashboard used to optimize train movements, surface audit logs, show platform status, predict conflicts, and expose queue and analytics data for visualization.

---

## Project Scope

- **Optimization API** to generate HOLD/PROCEED with paths and per-edge timelines
- **Dashboard GET endpoints** for platform status, train queue, current delays, predicted conflicts, audit logs, and train-type aggregates
- Hosted service available at the URL shown in the screenshots; all examples below mirror the payloads visible there

---

## Authentication

The sample `auth/check` API format in the screenshots demonstrates typical success/error shapes used across services where applicable.

---

## API: Optimize Timetable

**Method:** `POST`

**Endpoint:** `/optimize` (host root from screenshots)

### Request Body:

```json
{
  "name": "Proceed vs. Reroute Congestion",
  "trains": {
    "T1_Pass": {
      "type": "Passenger",
      "entry_node": "Entry_1",
      "exit_node": "Entry_12",
      "scheduled_entry_time": "2025-10-29T20:01:10",
      "scheduled_exit_time": "2025-10-29T20:01:40",
      "delay_factors": null
    },
    "T2_Local": {
      "type": "Local",
      "entry_node": "Entry_1",
      "exit_node": "Entry_9",
      "scheduled_entry_time": "2025-10-29T20:01:12",
      "scheduled_exit_time": "2025-10-29T20:01:45",
      "delay_factors": null
    }
  },
  "non_functional_segments": []
}
```

### Success Response:

```json
{
  "conflicts": [],
  "recommendations": [
    {
      "train_id": "T1_Pass",
      "action": "HOLD",
      "path": null,
      "total_delay_minutes": 0
    },
    {
      "train_id": "T2_Local",
      "action": "PROCEED",
      "path": [
        "Entry_1",
        "A",
        "P1_entry",
        "P1_exit",
        "F",
        "E",
        "Entry_9"
      ],
      "total_delay_minutes": 0.0
    }
  ],
  "score": 0.0,
  "timelines": {
    "T1_Pass": {},
    "T2_Local": {
      "A->P1_entry": [
        "Wed, 29 Oct 2025 20:04:12 GMT",
        "Wed, 29 Oct 2025 20:06:12 GMT"
      ],
      "E->Entry_9": [
        "Wed, 29 Oct 2025 20:19:42 GMT",
        "Wed, 29 Oct 2025 20:23:42 GMT"
      ]
    }
  }
}
```

---

## API: Platform Status

**Method:** `GET`

**Endpoint:** `/dashboard/platform_status`

### Response:

```json
[
  {
    "id": "Platform 1",
    "status": "available",
    "totalOccupancyMinutes": 0.0,
    "train": null
  },
  {
    "id": "Platform 2",
    "status": "available",
    "totalOccupancyMinutes": 0.0,
    "train": null
  },
  {
    "id": "Platform 3",
    "status": "available",
    "totalOccupancyMinutes": 0.0,
    "train": null
  }
]
```

---

## API: Train Queue

**Method:** `GET`

**Endpoint:** `/dashboard/train_queue`

### Response:

```json
[
  {
    "trainId": "T001",
    "priority": "Passenger",
    "platform": "Platform 1",
    "passengers": 850,
    "eta": "01:00",
    "status": "Holding"
  }
]
```

---

## API: Audit Data

**Method:** `GET`

**Endpoint:** `/dashboard/audit_data`

### Response (optimize-derived entries):

```json
[
  {
    "id": "AUD_892Q6F",
    "trainId": "T1_Pass",
    "priority": "Passenger",
    "section": "Junction N/A",
    "conflictType": "Clear Path",
    "aiRecommendation": "HOLD via path: ",
    "outcome": "Success - Final Delay: 0.00 min",
    "weatherCondition": "Clear",
    "linkedIncident": null
  },
  {
    "id": "AUD_2A6G37",
    "trainId": "T2_Local",
    "priority": "Local",
    "section": "Junction A",
    "conflictType": "Clear Path",
    "aiRecommendation": "PROCEED via path: Entry 1->A->P1_entry->P1_exit->F->E->Entry 9",
    "outcome": "Success - Final Delay: 0.00 min",
    "weatherCondition": "Clear",
    "linkedIncident": null
  }
]
```

### Response (single HOLD example):

```json
[
  {
    "id": "AUD_D759C2",
    "trainId": "T001",
    "priority": "Passenger",
    "section": "Junction N/A",
    "conflictType": "Clear Path",
    "aiRecommendation": "HOLD via path: ",
    "outcome": "Success - Final Delay: 0.00 min",
    "weatherCondition": "Clear",
    "linkedIncident": null
  }
]
```

---

## API: Predicted Conflicts

**Method:** `GET`

**Endpoint:** `/dashboard/predicted_conflicts`

---

## API: Current Delays

**Method:** `GET`

**Endpoint:** `/dashboard/current_delays`

---

## API: Train Type Data

**Method:** `GET`

**Endpoint:** `/dashboard/train_type_data`

### Response:

```json
[
  {
    "type": "Passenger",
    "count": 0,
    "avgDelay": 0.0
  },
  {
    "type": "Local",
    "count": 1,
    "avgDelay": 0.0
  }
]
```