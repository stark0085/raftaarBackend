import json
import os
from datetime import datetime, timedelta
import uuid

# The name of the local file that will act as our simple database
STATE_FILE = 'dashboard_state.json'

def update_and_get_dashboard_state(optimization_results, initial_train_data):
    """
    Transforms optimization results into all required data classes, saves to a
    local JSON file, and returns the live state. Now correctly handles timeline data.
    """
    recommendations = optimization_results.get('recommendations', [])
    conflicts = optimization_results.get('conflicts', [])
    timelines = optimization_results.get('timelines', {})
    now = datetime.now()

    # ==========================================================================
    # ** THE FIX IS HERE: Sanitize the timelines dictionary **
    # Convert tuple keys from the timeline into strings for JSON compatibility
    # ==========================================================================
    sanitized_timelines = {}
    for train_id, timeline in timelines.items():
        sanitized_timeline = {}
        for segment_tuple, (start, end) in timeline.items():
            # Convert tuple ('Entry_1', 'A') into string "Entry_1-A"
            segment_str = f"{segment_tuple[0]}-{segment_tuple[1]}"
            sanitized_timeline[segment_str] = {'start': start, 'end': end}
        sanitized_timelines[train_id] = sanitized_timeline
    # ==========================================================================

    # --- Sanitize the initial_train_data as before ---
    sanitized_initial_data = {}
    for tid, info in initial_train_data.items():
        sanitized_info = info.copy()
        if isinstance(info.get('scheduled_entry_time'), str):
            sanitized_info['scheduled_entry_time'] = datetime.fromisoformat(info['scheduled_entry_time'])
        sanitized_initial_data[tid] = sanitized_info

    # --- Data Class 3 & KPI: platformStatus (uses sanitized timelines) ---
    platform_events = {1: [], 2: [], 3: []}
    for train_id, timeline in sanitized_timelines.items():
        for segment_str, times in timeline.items():
            if 'P1_entry-P1_exit' in segment_str: platform_events[1].append({'start': times['start'], 'end': times['end'], 'train': train_id})
            if 'P2_entry-P2_exit' in segment_str: platform_events[2].append({'start': times['start'], 'end': times['end'], 'train': train_id})
            if 'P3_entry-P3_exit' in segment_str: platform_events[3].append({'start': times['start'], 'end': times['end'], 'train': train_id})

    platform_status, all_platform_times = [], []
    for p_num in range(1, 4):
        events = platform_events[p_num]
        total_occupancy_seconds = sum((e['end'] - e['start']).total_seconds() for e in events)
        status, current_train = 'available', None
        for event in events:
            if event['start'] <= now < event['end']:
                status, current_train = 'occupied', event['train']
                break
        platform_status.append({'id': f'Platform {p_num}', 'status': status, 'train': current_train, 'totalOccupancyMinutes': round(total_occupancy_seconds / 60, 2)})
        if events: all_platform_times.extend([e['start'] for e in events] + [e['end'] for e in events])
    total_station_operating_time = round((max(all_platform_times) - min(all_platform_times)).total_seconds() / 60, 2) if all_platform_times else 0

    # --- Other Data Classes (Logic remains the same, but uses sanitized inputs) ---
    current_delays = []
    for rec in recommendations:
        if rec['total_delay_minutes'] > 0:
            initial_info = sanitized_initial_data.get(rec['train_id'], {})
            if 'scheduled_entry_time' in initial_info:
                eta = (initial_info['scheduled_entry_time'] + timedelta(minutes=rec['total_delay_minutes'])).strftime('%H:%M')
                current_delays.append({'trainId': rec['train_id'], 'trainType': initial_info.get('type'),'delay': rec['total_delay_minutes'],'section': f"Junction {rec['path'][1] if rec['path'] and len(rec['path']) > 1 else 'Start'}",'eta': eta})

    train_queue = []
    status_map = {'PROCEED': 'Approaching', 'HOLD': 'Holding', 'REROUTED': 'Rerouted'}
    for rec in recommendations:
        tid = rec['train_id']
        initial_info = sanitized_initial_data.get(tid, {})
        if 'scheduled_entry_time' in initial_info:
            eta_time = (initial_info['scheduled_entry_time'] + timedelta(minutes=rec.get('total_delay_minutes', 0)))
            train_queue.append({'trainId': tid,'priority': initial_info.get('type', 'Unknown'),'status': status_map.get(rec['action'], 'Scheduled'),'platform': f"Platform {tid[-1]}",'eta': eta_time.strftime('%H:%M'),'passengers': 850 if 'Pass' in initial_info.get('type', '') else 0})

    predicted_conflicts = conflicts
    
    train_type_agg = {}
    for rec in recommendations:
        train_type = sanitized_initial_data.get(rec['train_id'], {}).get('type')
        if train_type:
            if train_type not in train_type_agg: train_type_agg[train_type] = {'delays': [], 'passed_count': 0}
            train_type_agg[train_type]['delays'].append(rec['total_delay_minutes'])
            if rec['action'] != 'HOLD': train_type_agg[train_type]['passed_count'] += 1
    train_type_summary = []
    for t_type, data in train_type_agg.items():
        avg_delay = sum(data['delays']) / len(data['delays']) if data['delays'] else 0
        train_type_summary.append({'type': t_type, 'avgDelay': round(avg_delay, 2), 'count': data['passed_count']})

    audit_data = []
    for rec in recommendations:
        initial_info = sanitized_initial_data.get(rec['train_id'], {})
        audit_data.append({'id': f"AUD_{str(uuid.uuid4().hex)[:6].upper()}",'trainId': rec['train_id'],'section': f"Junction {rec['path'][1] if rec['path'] and len(rec['path']) > 1 else 'N/A'}",'aiRecommendation': f"{rec['action']} via path: {'->'.join(rec['path'] or [])}",'outcome': f"Success - Final Delay: {rec['total_delay_minutes']:.2f} min",'conflictType': 'Priority Crossing' if rec['total_delay_minutes'] > 0 else 'Clear Path','priority': initial_info.get('type', 'Unknown'),'weatherCondition': 'Clear', 'linkedIncident': None})

    # --- Assemble and save the final state ---
    live_state = {
        'kpis': {'totalStationOperatingTimeMinutes': total_station_operating_time},
        'currentDelays': current_delays,'trainQueue': train_queue,'platformStatus': platform_status,
        'predictedConflicts': predicted_conflicts,'trainTypeData': train_type_summary,'auditData': audit_data,
        'last_updated': datetime.now()
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(live_state, f, indent=2, default=str)
    print(f"Live dashboard state has been updated in '{STATE_FILE}'.")
    return live_state

def get_dashboard_data_class(class_name):
    if not os.path.exists(STATE_FILE): return []
    try:
        with open(STATE_FILE, 'r') as f: data = json.load(f)
        return data.get(class_name, [])
    except (json.JSONDecodeError, FileNotFoundError): return []

