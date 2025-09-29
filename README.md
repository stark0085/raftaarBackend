SIH Train Delay Minimization - OR Module

This project contains the core Operations Research (OR) module for the Smart India Hackathon train delay minimization problem. It uses a Simulated Annealing metaheuristic to find near-optimal schedules for trains in a complex railway network, aiming to maximize throughput while minimizing total delay. The logic is exposed via a simple Flask API for easy integration with other services, such as a live dashboard.

Features

Dynamic Pathfinding: Automatically finds all possible routes for a train, including rerouting links, and can adapt to track failures.

Sophisticated Conflict Detection: A detailed event-based simulation detects both track and junction (node) conflicts.

Intelligent Rerouting: The optimizer can reroute trains to different platforms or paths to avoid congestion or non-functional tracks, finding globally optimal solutions.

Priority Handling: Correctly respects train precedence (e.g., Special > Passenger > Freight), ensuring high-priority trains are given the right-of-way.

Handles External Delays: Can factor in initial delays predicted by an ML model (e.g., weather delays) to produce a more realistic schedule.

API-Ready: All logic is wrapped in a Flask API, providing a clean interface for a UI dashboard or other services.

Live Dashboard Backend: Provides a suite of API endpoints to power a real-time dashboard with KPIs, train queues, platform status, and more.


Setup and Installation

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

Prerequisites

Python 3.8+

pip and virtualenv


Instructions

Clone the repository:
git clone https://github.com/krishjaiman
cd or-module


Create and activate a virtual environment:
This isolates the project's dependencies.# On macOS/Linux
python3 -m venv venv

source venv/bin/activate

# On Windows

python -m venv venv

.\venv\Scripts\activate


Install the required dependencies:

pip install -r requirements.txt


Run the Server:

Start the Flask API server with this command:

python main.py
If it starts successfully, you will see a message indicating it's running on http://127.0.0.1:5000/.

API Usage GuideThe backend exposes a simple API for running the optimization and fetching dashboard data.
Triggering the Optimization (POST)To run the optimizer, the UI must send the current state of all trains. This triggers the simulation and updates the live dashboard data stored in dashboard_state.json.URL: http://127.0.0.1:5000/optimize

 Method: POST
 
 Body (JSON Example):Note: Timestamps must be in ISO 8601 format.

 {
    "trains": {
   
        "T1_Pass": {
            "type": "Passenger",
            "entry_node": "Entry_1",
            "exit_node": "Entry_12",
            "scheduled_entry_time": "2025-09-29T18:05:00",
            "scheduled_exit_time": "2025-09-29T18:30:00"
        },
   
        "T2_Frt": {
            "type": "Freight",
            "entry_node": "Entry_4",
            "exit_node": "Entry_10",
            "scheduled_entry_time": "2025-09-29T18:06:00",
            "scheduled_exit_time": "2025-09-29T18:40:00"
        }
    },
   
    "non_functional_segments": [["A", "P1_entry"]]
}
7. Fetching Dashboard Data (GET):

After the **/optimize** call is complete, the UI can fetch the updated data for each of its components using the following GET endpoints.

Endpoint                              Data Returned

/dashboard/current_delays     An array of all trains that currently have a delay./dashboard/train_queueAn array of all trains in the system, with their current status.

/dashboard/platform_status        An array showing the live status of each platform./dashboard/predicted_conflictsAn array of all conflicts the optimizer detected and resolved.

/dashboard/train_type_data         An array of summary statistics for each train type./dashboard/audit_dataAn array of detailed log entries for each decision.

Example: To populate the "Train Queue" component, the UI would make a GET request to http://127.0.0.1:5000/dashboard/train_queue.

3. Making the Dashboard "Live"To keep the dashboard updated, the UI application should have a timer (e.g., using setInterval in JavaScript) that repeats the POST and GET workflow every 10-30 seconds. This polling mechanism ensures that the dashboard is always showing a fresh, optimized state.
