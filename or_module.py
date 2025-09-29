import networkx as nx
import random
import math
import copy
from datetime import datetime, timedelta
import sys
import heapq
from itertools import islice

# ==============================================================================
# 0. GLOBAL CONSTANTS
# ==============================================================================
TRAIN_PRECEDENCE = {
    'Special': 4,
    'Passenger': 3,
    'Local': 2,
    'Freight': 1
}

# ==============================================================================
# 1. CORE CLASSES
# ==============================================================================
class DelayFactors:
    def __init__(self, is_track_functional=True, chain_pull_delay=0, loco_pilot_delay=0, ml_weather_delay=0):
        self.chain_pull_delay = chain_pull_delay
        self.loco_pilot_delay = loco_pilot_delay
        self.ml_weather_delay = ml_weather_delay
    def total_delay(self):
        return self.chain_pull_delay + self.loco_pilot_delay + self.ml_weather_delay

class NetworkTimeState:
    def __init__(self):
        self.edge_travel_times = {
            ('Entry_1', 'A'): 3, ('Entry_4', 'A'): 2, ('Entry_2', 'B'): 4, ('Entry_5', 'B'): 3,
            ('Entry_3', 'C'): 5, ('Entry_6', 'C'): 3, ('F', 'Entry_10'): 3, ('F', 'Entry_12'): 3,
            ('E', 'Entry_9'): 4, ('E', 'Entry_11'): 2, ('D', 'Entry_7'): 2, ('D', 'Entry_8'): 4,
            ('A', 'P1_entry'): 2, ('P1_exit', 'F'): 2, ('B', 'P2_entry'): 2, ('P2_exit', 'E'): 2,
            ('C', 'P3_entry'): 2, ('P3_exit', 'D'): 2, ('A', 'B'): 1.5, ('B', 'A'): 1.5,
            ('E', 'F'): 1.5, ('F', 'E'): 1.5, ('P1_entry', 'P1_exit'): 5,
            ('P2_entry', 'P2_exit'): 5, ('P3_entry', 'P3_exit'): 5,
        }
        self.dwell_times = {'Passenger': 3, 'Special': 2, 'Freight': 8, 'Local': 5}

class TrainJourney:
    def __init__(self, train_id, entry_node, exit_node, scheduled_entry_time,
                 train_type, network_state, scheduled_exit_time=None, non_functional_segments=None, delay_factors=None):
        self.train_id = train_id
        self.entry_node = entry_node
        self.exit_node = exit_node
        self.scheduled_entry_time = scheduled_entry_time
        self.train_type = train_type
        self.delay_factors = delay_factors or DelayFactors()
        self.actual_arrival_time = scheduled_entry_time + timedelta(minutes=self.delay_factors.total_delay())
        ideal_graph = create_graph_from_data(network_state)
        ideal_paths = find_all_possible_paths(ideal_graph, self.entry_node, self.exit_node)
        self.ideal_path = min(ideal_paths, key=len) if ideal_paths else None
        current_graph = create_graph_from_data(network_state, non_functional_segments)
        self.possible_paths = find_all_possible_paths(current_graph, self.entry_node, self.exit_node)
        self.default_path = min(self.possible_paths, key=len) if self.possible_paths else None

# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================
def create_graph_from_data(network_state, non_functional_segments=None):
    G = nx.DiGraph()
    non_functional = non_functional_segments or set()
    for edge, time in network_state.edge_travel_times.items():
        if edge not in non_functional:
            G.add_edge(edge[0], edge[1], weight=time)
    return G

def find_all_possible_paths(graph, start_node, end_node):
    try:
        return list(islice(nx.all_simple_paths(graph, source=start_node, target=end_node), 5))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

# ==============================================================================
# 3. CORE OR ALGORITHM
# ==============================================================================
class PathBasedSolution:
    def __init__(self, train_journeys):
        self.train_journeys = {tj.train_id: tj for tj in train_journeys}
        self.decisions = {}
        for tid, journey in self.train_journeys.items():
            self.decisions[tid] = {'action': 'PROCEED', 'path': journey.default_path} if journey.possible_paths else {'action': 'HOLD', 'path': None}

def calculate_objective_cost(solution, network_state):
    track_occupancy, node_occupancy = {}, {}
    individual_delays = {tid: 0 for tid in solution.train_journeys.keys()}
    event_queue, conflicts_detected = [], []
    actual_finish_times = {}
    actual_timelines = {tid: {} for tid in solution.train_journeys.keys()}
    for tid, decision in solution.decisions.items():
        if decision['action'] == 'PROCEED' and decision['path']:
            heapq.heappush(event_queue, (solution.train_journeys[tid].actual_arrival_time, tid, 0))
    processed_events = {}
    while event_queue:
        current_time, train_id, path_idx = heapq.heappop(event_queue)
        path = solution.decisions[train_id]['path']
        if path_idx >= len(path) - 1:
            actual_finish_times[train_id] = current_time
            continue
        segment = (path[path_idx], path[path_idx + 1])
        start_node, end_node = segment
        last_track_exit, track_holder = track_occupancy.get(segment, (datetime.min, None))
        last_node_exit, node_holder = node_occupancy.get(start_node, (datetime.min, None))
        entry_time = max(current_time, last_track_exit, last_node_exit)
        wait_time = (entry_time - current_time).total_seconds() / 60
        if wait_time > 0.1:
            conflicting_train = track_holder if last_track_exit > last_node_exit else node_holder
            if conflicting_train and (train_id, conflicting_train) not in processed_events:
                conflicts_detected.append({'time': entry_time.strftime('%H:%M'), 'trains': [train_id, conflicting_train], 'location': f"Junction {start_node}", 'severity': 'medium', 'resolution': f"HOLD {train_id} for {wait_time:.2f} min"})
                processed_events[(train_id, conflicting_train)] = True
        individual_delays[train_id] += wait_time
        journey = solution.train_journeys[train_id]
        travel_time = network_state.edge_travel_times.get(segment, 2)
        if start_node.endswith('_entry'):
            travel_time += network_state.dwell_times.get(journey.train_type, 3)
        exit_time = entry_time + timedelta(minutes=travel_time)
        track_occupancy[segment] = (exit_time, train_id)
        node_occupancy[end_node] = (exit_time, train_id)
        actual_timelines[train_id][segment] = (entry_time, exit_time)
        heapq.heappush(event_queue, (exit_time, train_id, path_idx + 1))

    total_delay, throughput_bonus = 0, 0
    for tid, decision in solution.decisions.items():
        journey = solution.train_journeys[tid]
        if decision['action'] == 'PROCEED' and decision['path']:
            total_delay += individual_delays[tid]
            throughput_bonus += 100
        else:
            latest_clear_time = journey.actual_arrival_time
            for other_tid, finish_time in actual_finish_times.items():
                if TRAIN_PRECEDENCE.get(solution.train_journeys[other_tid].train_type, 0) >= TRAIN_PRECEDENCE.get(journey.train_type, 0):
                    if finish_time > latest_clear_time: latest_clear_time = finish_time
            held_delay = (latest_clear_time - journey.actual_arrival_time).total_seconds() / 60
            individual_delays[tid] = max(0, held_delay)
            total_delay += individual_delays[tid]
    return total_delay - throughput_bonus, individual_delays, conflicts_detected, actual_timelines

def generate_neighbor(solution):
    neighbor = copy.deepcopy(solution)
    if random.random() < 0.5:
        reroutable = [tid for tid, d in neighbor.decisions.items() if d['action'] == 'PROCEED' and len(neighbor.train_journeys[tid].possible_paths) > 1]
        if reroutable:
            tid = random.choice(reroutable)
            current_path = neighbor.decisions[tid]['path']
            new_paths = [p for p in neighbor.train_journeys[tid].possible_paths if p != current_path]
            if new_paths: neighbor.decisions[tid]['path'] = random.choice(new_paths)
    else:
        tid = random.choice(list(neighbor.decisions.keys()))
        if neighbor.decisions[tid]['action'] == 'PROCEED':
            neighbor.decisions[tid]['action'] = 'HOLD'; neighbor.decisions[tid]['path'] = None
        elif neighbor.train_journeys[tid].possible_paths:
            neighbor.decisions[tid]['action'] = 'PROCEED'; neighbor.decisions[tid]['path'] = neighbor.train_journeys[tid].default_path
    return neighbor

def simulated_annealing(train_journeys, network_state, iterations=2000, temp=1000, cool_rate=0.99):
    current_sol = PathBasedSolution(train_journeys)
    current_cost, _, _, _ = calculate_objective_cost(current_sol, network_state)
    best_sol, best_cost = current_sol, current_cost
    for _ in range(iterations):
        if temp <= 0.01: break
        neighbor = generate_neighbor(current_sol)
        neighbor_cost, _, _, _ = calculate_objective_cost(neighbor, network_state)
        delta = neighbor_cost - current_cost
        if delta < 0 or random.random() < math.exp(-delta / temp):
            current_sol, current_cost = neighbor, neighbor_cost
            if current_cost < best_cost: best_sol, best_cost = copy.deepcopy(current_sol), current_cost
        temp *= cool_rate
    return best_sol

# ==============================================================================
# 4. MAIN EXECUTION & REPORTING
# ==============================================================================
def execute_module(train_data, non_functional_segments=None):
    """
    Main entry point for the OR module. It now safely handles and sanitizes
    the input data before running the optimization.
    """
    network_state = NetworkTimeState()
    train_journeys = []

    for tid, info in train_data.items():
        try:
            # --- Robust Data Sanitization ---
            entry_time_str = info['scheduled_entry_time']
            entry_time_obj = datetime.fromisoformat(entry_time_str)

            exit_time_obj = None
            if 'scheduled_exit_time' in info and info['scheduled_exit_time']:
                exit_time_obj = datetime.fromisoformat(info['scheduled_exit_time'])

            delay_factors_data = info.get('delay_factors')
            delay_factors_obj = DelayFactors(**delay_factors_data) if isinstance(delay_factors_data, dict) else DelayFactors()

            train_journeys.append(TrainJourney(
                train_id=tid,
                entry_node=info['entry_node'],
                exit_node=info['exit_node'],
                scheduled_entry_time=entry_time_obj,
                scheduled_exit_time=exit_time_obj,
                train_type=info['type'],
                delay_factors=delay_factors_obj,
                network_state=network_state,
                non_functional_segments=non_functional_segments
            ))
        except (KeyError, TypeError, ValueError) as e:
            print(f"CRITICAL ERROR: Malformed data for train {tid}. Reason: {e}")
            raise ValueError(f"Malformed data for train {tid}")

    best_solution = simulated_annealing(train_journeys, network_state)
    _, final_delays, conflicts, final_timelines = calculate_objective_cost(best_solution, network_state)
    final_score = sum(final_delays.values())
    
    # *** FIX: Convert tuple keys to strings for JSON serialization ***
    json_safe_timelines = {}
    for train_id, segments in final_timelines.items():
        json_safe_timelines[train_id] = {}
        for seg, (start, end) in segments.items():
            # Convert tuple keys like ('Entry_1', 'A') to string keys like "Entry_1->A"
            segment_key = f"{seg[0]}->{seg[1]}"
            # Keep datetime objects as-is for now (dashboard_data_manager will handle them)
            json_safe_timelines[train_id][segment_key] = (start, end)
    # *** END FIX ***
    
    recommendations = []
    for tid, data in best_solution.decisions.items():
        journey = best_solution.train_journeys[tid]
        action = data['action']
        if action == 'PROCEED' and journey.ideal_path and data['path'] != journey.ideal_path:
            action = 'REROUTED'
        recommendations.append({
            'train_id': tid, 
            'action': action, 
            'path': data['path'], 
            'total_delay_minutes': round(final_delays.get(tid, 0), 2)
        })
        
    return {
        'score': round(final_score, 2), 
        'recommendations': recommendations, 
        'solution': best_solution, 
        'conflicts': conflicts, 
        'timelines': json_safe_timelines  # Use the converted version
    }