SIH Train Delay Minimization - OR Module
This project contains the core Operations Research (OR) module for the Smart India Hackathon train delay minimization problem. It uses a Simulated Annealing metaheuristic to find near-optimal schedules for trains in a complex railway network, aiming to maximize throughput while minimizing total delay.
The logic is exposed via a simple Flask API for easy integration with other services.
Features:
Dynamic Pathfinding: Automatically finds all possible routes for a train, including rerouting links.
Conflict Detection: A sophisticated event-based simulation detects both track and junction (node) conflicts.
Intelligent Rerouting: Can reroute trains to avoid congestion or non-functional tracks.
Priority Handling: Respects train precedence (e.g., Special > Passenger > Freight).Handles External Delays: Can factor in initial delays predicted by an ML model (e.g., weather delays).
API-Ready: All logic is wrapped in a Flask API for easy testing and integration.


Setup and Installation:
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

Prerequisites:
Python 3.8+
pip and virtualenv

Instructions:
Clone the repository: 
git clone https://github.com/krishjaiman/sih-or-module
cd or-module


Create and activate a virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

Install the required dependencies:
pip install -r requirements.txt


Running the API Server: 
To start the local development server:
Make sure your virtual environment is activated.
Run the main.py script:python main.py
The server will start and be accessible at http://127.0.0.1:5000.

Using the API:
You can test the API using a tool like curl or Postman.
Endpoint
URL: /optimize
Method: POST
Body: Raw JSON


ExampleRequest
Here is an example curl command. Note that datetimes must be in ISO 8601 format.

curl -X POST http://127.0.0.1:5000/optimize \
-H "Content-Type: application/json" \
-d '{
    "trains": {
        "T1_Pass": {
            "type": "Passenger",
            "entry_node": "Entry_1",
            "exit_node": "Entry_12",
            "scheduled_entry_time": "2025-09-29T12:40:00",
            "scheduled_exit_time": "2025-09-29T13:05:00",
            "delay_factors": null
        },
        "T2_Local": {
            "type": "Local",
            "entry_node": "Entry_4",
            "exit_node": "Entry_9",
            "scheduled_entry_time": "2025-09-29T12:41:00",
            "scheduled_exit_time": "2025-09-29T13:15:00",
            "delay_factors": null
        },
        "T3_Frt": {
            "type": "Freight",
            "entry_node": "Entry_5",
            "exit_node": "Entry_11",
            "scheduled_entry_time": "2025-09-29T12:43:00",
            "scheduled_exit_time": "2025-09-29T13:25:00",
            "delay_factors": null
        }
    },
    "non_functional_segments": []
}'


Example Success Response{
  "recommendations": [
    {
      "action": "PROCEED",
      "path": ["Entry_1", "A", "P1_entry", "P1_exit", "F", "Entry_12"],
      "total_delay_minutes": 0.0,
      "train_id": "T1_Pass"
    },
    {
      "action": "REROUTED",
      "path": ["Entry_4", "A", "B", "P2_entry", "P2_exit", "E", "Entry_9"],
      "total_delay_minutes": 0.0,
      "train_id": "T2_Local"
    },
    {
      "action": "PROCEED",
      "path": ["Entry_5", "B", "P2_entry", "P2_exit", "E", "Entry_11"],
      "total_delay_minutes": 8.5,
      "train_id": "T3_Frt"
    }
  ],
  "score": 8.5
}
