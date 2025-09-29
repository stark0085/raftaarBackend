import json
import os
from datetime import datetime, timedelta
import uuid

# The name of the local file that will act as our simple database
STATE_FILE = 'dashboard_state.json'

def update_and_get_dashboard_state(optimization_results, initial_train_data):
    """
    Takes the full output of the OR module, transforms it into all the required
    data classes for the dashboard, saves it to a local JSON file, and returns the live state.
    """
    recommendations = optimization_results.get('recommendations', [])
    conflicts = optimization_results.get('conflicts', [])
    timelines = optimization_results.get('timelines', {})
    now = datetime.now()

    # ==========================================================================
    # DATA CLASS 3 & KPI: platformStatus and Occupancy Calculation
    # ==========================================================================
    platform_events = {1: [], 2: [], 3: []}
    for train_id, timeline in timelines.items():
        for segment, (start, end) in timeline.items():
            if segment == ('P1_entry', 'P1_exit'): platform_events[1].append({'start': start, 'end': end, 'train': train_id})
            if segment == ('P2_entry', 'P2_exit'): platform_events[2].append({'start': start, 'end': end, 'train': train_id})
            if segment == ('P3_entry', 'P3_exit'): platform_events[3].append({'start': start, 'end': end, 'train': train_id})

    platform_status = []
    all_platform_times = []
    for p_num in range(1, 4):
        events = platform_events[p_num]
        total_occupancy_seconds = sum((e['end'] - e['start']).total_seconds() for e in events)
        
        current_train_on_platform = None
        status = 'available'
        for event in events:
            if event['start'] <= now < event['end']:
                status = 'occupied'
                current_train_on_platform = event['train']
                break
        
        platform_status.append({
            'id': f'Platform {p_num}',
            'status': status,
            'train': current_train_on_platform,
            'totalOccupancyMinutes': round(total_occupancy_seconds / 60, 2)
        })
        if events:
            all_platform_times.extend([e['start'] for e in events] + [e['end'] for e in events])

    total_station_operating_time = 0
    if all_platform_times:
        first_entry = min(all_platform_times)
        last_exit = max(all_platform_times)
        total_station_operating_time = round((last_exit - first_entry).total_seconds() / 60, 2)

    # ==========================================================================
    # DATA CLASS 1: currentDelays
    # ==========================================================================
    current_delays = []
    for rec in recommendations:
        if rec['total_delay_minutes'] > 0:
            initial_info = initial_train_data.get(rec['train_id'], {})
            eta = (initial_info['scheduled_entry_time'] + timedelta(minutes=rec['total_delay_minutes'])).strftime('%H:%M')
            current_delays.append({
                'trainId': rec['train_id'],
                'trainType': initial_info.get('type'),
                'delay': rec['total_delay_minutes'],
                'section': f"Approach to Junction {rec['path'][1] if rec['path'] and len(rec['path']) > 1 else 'Start'}",
                'eta': eta
            })

    # ==========================================================================
    # DATA CLASS 2: trainQueue
    # ==========================================================================
    train_queue = []
    status_map = {'PROCEED': 'Approaching', 'HOLD': 'Holding', 'REROUTED': 'Rerouted'}
    for rec in recommendations:
        tid = rec['train_id']
        initial_info = initial_train_data.get(tid, {})
        # ETA is based on initial schedule + calculated delay
        eta_time = (initial_info['scheduled_entry_time'] + timedelta(minutes=rec.get('total_delay_minutes', 0)))
        train_queue.append({
            'trainId': tid,
            'priority': initial_info.get('type', 'Unknown'),
            'status': status_map.get(rec['action'], 'Scheduled'),
            'platform': f"Platform {tid[-1]}", # Simple logic based on train ID
            'eta': eta_time.strftime('%H:%M'),
            'passengers': 850 if 'Pass' in initial_info.get('type', '') else 0
        })

    # ==========================================================================
    # DATA CLASS 4: predictedConflicts
    # ==========================================================================
    predicted_conflicts = conflicts

    # ==========================================================================
    # DATA CLASS 5: trainTypeData
    # ==========================================================================
    train_type_agg = {}
    for rec in recommendations:
        tid = rec['train_id']
        initial_info = initial_train_data.get(tid, {})
        train_type = initial_info.get('type')
        if train_type not in train_type_agg:
            train_type_agg[train_type] = {'delays': [], 'passed_count': 0}
        train_type_agg[train_type]['delays'].append(rec['total_delay_minutes'])
        if rec['action'] != 'HOLD':
            train_type_agg[train_type]['passed_count'] += 1
    
    train_type_summary = []
    for t_type, data in train_type_agg.items():
        avg_delay = sum(data['delays']) / len(data['delays']) if data['delays'] else 0
        train_type_summary.append({'type': t_type, 'avgDelay': round(avg_delay, 2), 'count': data['passed_count']})

    # ==========================================================================
    # DATA CLASS 6: auditData
    # ==========================================================================
    audit_data = []
    for rec in recommendations:
        initial_info = initial_train_data.get(rec['train_id'], {})
        audit_data.append({
            'id': f"AUD_{str(uuid.uuid4().hex)[:6].upper()}",
            'trainId': rec['train_id'],
            'section': f"Junction {rec['path'][1] if rec['path'] and len(rec['path']) > 1 else 'N/A'}",
            'aiRecommendation': f"{rec['action']} via path: {'->'.join(rec['path'] if rec['path'] else [])}",
            'outcome': f"Success - Final Delay: {rec['total_delay_minutes']:.2f} min",
            'conflictType': 'Priority Crossing' if rec['total_delay_minutes'] > 0 else 'Clear Path',
            'priority': initial_info.get('type', 'Unknown'),
            'weatherCondition': 'Clear', 'linkedIncident': None
        })

    # --- Assemble and save the complete state to the local JSON file ---
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
    
    with open(STATE_FILE, 'w') as f:
        json.dump(live_state, f, indent=2, default=str)

    print(f"Live dashboard state has been updated in '{STATE_FILE}'.")
    return live_state

def get_dashboard_data_class(class_name):
    """Generic function to fetch a specific data class from the local JSON file."""
    if not os.path.exists(STATE_FILE):
        return []
    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
        return data.get(class_name, [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []

