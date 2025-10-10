import json
import os
import redis
from datetime import datetime, timedelta
import uuid
from dotenv import load_dotenv

# --- New: Redis Configuration ---
# Load environment variables from a .env file for local development
load_dotenv()

# Get the Redis connection URL from environment variables.
# This works both locally (reads from .env) and on Vercel (reads from project settings).
REDIS_URL = os.environ.get('REDIS_URL')

# Raise an error if the URL isn't found, as the app can't function without it.
if not REDIS_URL:
    raise ValueError("FATAL ERROR: REDIS_URL environment variable is not set.")

# Establish a connection to your Upstash Redis database.
redis_client = redis.from_url(REDIS_URL)

# Define the single key we will use to store the entire dashboard state in Redis.
REDIS_DASHBOARD_KEY = "dashboard_live_state"


def update_and_get_dashboard_state(optimization_results, initial_train_data):
    """
    Takes the full output of the OR module, transforms it into all the required
    data classes for the dashboard, saves it to REDIS, and returns the live state.
    """
    # ==========================================================================
    # All of your data processing logic below remains UNCHANGED.
    # It correctly calculates the state. We only change how it's saved at the end.
    # ==========================================================================
    
    recommendations = optimization_results.get('recommendations', [])
    conflicts = optimization_results.get('conflicts', [])
    timelines_raw = optimization_results.get('timelines', {})
    now = datetime.now()

    # ** CONVERT TIMELINES **
    timelines = {}
    for train_id, segments in timelines_raw.items():
        timelines[train_id] = {}
        for segment_key, (start_val, end_val) in segments.items():
            if isinstance(start_val, str):
                start_dt = datetime.fromisoformat(start_val)
                end_dt = datetime.fromisoformat(end_val)
            else:
                start_dt, end_dt = start_val, end_val
            timelines[train_id][segment_key] = (start_dt, end_dt)

    # ** Sanitize the input data **
    sanitized_initial_data = {}
    for tid, info in initial_train_data.items():
        sanitized_info = info.copy()
        if isinstance(info.get('scheduled_entry_time'), str):
            sanitized_info['scheduled_entry_time'] = datetime.fromisoformat(info['scheduled_entry_time'])
        if isinstance(info.get('scheduled_exit_time'), str):
            sanitized_info['scheduled_exit_time'] = datetime.fromisoformat(info['scheduled_exit_time'])
        sanitized_initial_data[tid] = sanitized_info

    # --- Data Class 1: currentDelays ---
    current_delays = []
    for rec in recommendations:
        if rec['total_delay_minutes'] > 0:
            initial_info = sanitized_initial_data.get(rec['train_id'], {})
            if 'scheduled_entry_time' in initial_info:
                eta = (initial_info['scheduled_entry_time'] + timedelta(minutes=rec['total_delay_minutes'])).strftime('%H:%M')
                current_delays.append({
                    'trainId': rec['train_id'],
                    'trainType': initial_info.get('type'),
                    'delay': rec['total_delay_minutes'],
                    'section': f"Junction near {rec['path'][1] if rec['path'] and len(rec['path']) > 1 else 'Start'}",
                    'eta': eta
                })

    # --- Data Class 2: trainQueue ---
    train_queue = []
    status_map = {'PROCEED': 'Approaching', 'HOLD': 'Holding', 'REROUTED': 'Rerouted'}
    for rec in recommendations:
        tid = rec['train_id']
        initial_info = sanitized_initial_data.get(tid, {})
        if 'scheduled_entry_time' in initial_info:
            eta_time = (initial_info['scheduled_entry_time'] + timedelta(minutes=rec.get('total_delay_minutes', 0)))
            train_queue.append({
                'trainId': tid,
                'priority': initial_info.get('type', 'Unknown'),
                'status': status_map.get(rec['action'], 'Scheduled'),
                'platform': f"Platform {tid[-1]}", # Simple logic
                'eta': eta_time.strftime('%H:%M'),
                'passengers': 850 if 'Pass' in initial_info.get('type', '') else 0
            })
    
    # --- Data Class 3 & KPI: platformStatus and Occupancy Calculation ---
    platform_events = {1: [], 2: [], 3: []}
    for train_id, timeline in timelines.items():
        for segment_key, (start, end) in timeline.items():
            if 'P1_entry' in segment_key and 'P1_exit' in segment_key:
                platform_events[1].append({'start': start, 'end': end, 'train': train_id})
            elif 'P2_entry' in segment_key and 'P2_exit' in segment_key:
                platform_events[2].append({'start': start, 'end': end, 'train': train_id})
            elif 'P3_entry' in segment_key and 'P3_exit' in segment_key:
                platform_events[3].append({'start': start, 'end': end, 'train': train_id})
    
    platform_status, all_platform_times = [], []
    for p_num in range(1, 4):
        events = platform_events[p_num]
        total_occupancy_seconds = sum((e['end'] - e['start']).total_seconds() for e in events)
        status, current_train = 'available', None
        for event in events:
            if event['start'] <= now < event['end']:
                status, current_train = 'occupied', event['train']
                break
        platform_status.append({
            'id': f'Platform {p_num}', 
            'status': status, 
            'train': current_train, 
            'totalOccupancyMinutes': round(total_occupancy_seconds / 60, 2)
        })
        if events: 
            all_platform_times.extend([e['start'] for e in events] + [e['end'] for e in events])
    
    total_station_operating_time = round((max(all_platform_times) - min(all_platform_times)).total_seconds() / 60, 2) if all_platform_times else 0

    # --- Data Class 4: predictedConflicts ---
    predicted_conflicts = conflicts

    # --- Data Class 5: trainTypeData ---
    train_type_agg = {}
    for rec in recommendations:
        train_type = sanitized_initial_data.get(rec['train_id'], {}).get('type')
        if train_type:
            if train_type not in train_type_agg: 
                train_type_agg[train_type] = {'delays': [], 'passed_count': 0}
            train_type_agg[train_type]['delays'].append(rec['total_delay_minutes'])
            if rec['action'] != 'HOLD': 
                train_type_agg[train_type]['passed_count'] += 1
    
    train_type_summary = []
    for t_type, data in train_type_agg.items():
        avg_delay = sum(data['delays']) / len(data['delays']) if data['delays'] else 0
        train_type_summary.append({
            'type': t_type, 
            'avgDelay': round(avg_delay, 2), 
            'count': data['passed_count']
        })

    # --- Data Class 6: auditData ---
    audit_data = []
    for rec in recommendations:
        initial_info = sanitized_initial_data.get(rec['train_id'], {})
        audit_data.append({
            'id': f"AUD_{str(uuid.uuid4().hex)[:6].upper()}",
            'trainId': rec['train_id'],
            'section': f"Junction {rec['path'][1] if rec['path'] and len(rec['path']) > 1 else 'N/A'}",
            'aiRecommendation': f"{rec['action']} via path: {'->'.join(rec['path'] or [])}",
            'outcome': f"Success - Final Delay: {rec['total_delay_minutes']:.2f} min",
            'conflictType': 'Priority Crossing' if rec['total_delay_minutes'] > 0 else 'Clear Path',
            'priority': initial_info.get('type', 'Unknown'),
            'weatherCondition': 'Clear', 
            'linkedIncident': None
        })

    # --- Assemble the final state ---
    live_state = {
        'kpis': {'totalStationOperatingTimeMinutes': total_station_operating_time},
        'currentDelays': current_delays,
        'trainQueue': train_queue,
        'platformStatus': platform_status,
        'predictedConflicts': predicted_conflicts,
        'trainTypeData': train_type_summary,
        'auditData': audit_data,
        'last_updated': datetime.now()
    }
    
    # --- Changed: Save to Redis instead of a local file ---
    try:
        # Convert the dictionary to a JSON string. `default=str` is crucial
        # to handle datetime objects that are not natively JSON serializable.
        state_as_json_string = json.dumps(live_state, indent=2, default=str)
        
        # Store the JSON string in Redis under our predefined key.
        redis_client.set(REDIS_DASHBOARD_KEY, state_as_json_string)
        
        print(f"Live dashboard state has been updated in Redis.")

    except Exception as e:
        print(f"ERROR: Could not save state to Redis. Reason: {e}")
        # Optionally, re-raise the exception if this is a critical failure
        # raise e
    
    return live_state


def get_dashboard_data_class(class_name):
    """
    Fetches the entire dashboard state from Redis, then returns the specific
    data class (e.g., 'platformStatus') that was requested.
    """
    try:
        # --- Changed: Read from Redis instead of a local file ---
        # Retrieve the JSON string from our key in Redis
        state_as_json_string = redis_client.get(REDIS_DASHBOARD_KEY)

        # If the key doesn't exist in Redis yet, it means the /optimize
        # endpoint hasn't been called. Return an empty list as a safe default.
        if state_as_json_string is None:
            return []
        
        # If data was found, parse the JSON string back into a Python dictionary
        data = json.loads(state_as_json_string)
        
        # Return the specific list/value for the requested class_name.
        # .get() is used to safely return an empty list if the key isn't in the data.
        return data.get(class_name, [])

    except Exception as e:
        print(f"ERROR: Could not retrieve or parse state from Redis. Reason: {e}")
        # Return an empty list to prevent the frontend from crashing on an error.
        return []
