from flask import Flask, request, jsonify
<<<<<<< HEAD
from flask_cors import CORS  # Import the CORS library
from or_module import execute_module, DelayFactors
from datetime import datetime
=======
from or_module import execute_module
from dashboard_data_manager import update_and_get_dashboard_state, get_dashboard_data_class
>>>>>>> 85e58cc6b427e8889931461f0572eb93d128ccde

app = Flask(__name__)
# Explicitly allow all origins ('*') to access all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# ==============================================================================
# 1. Main Optimizer Endpoint
# ==============================================================================
@app.route('/optimize', methods=['POST'])
def optimize_schedule():
    """
    Receives train data, runs the optimization, updates the live dashboard state,
    and returns the schedule recommendations.
    """
    train_data = request.get_json()
    if not train_data or 'trains' not in train_data:
        return jsonify({"error": "Invalid input"}), 400

    non_functional_segments = train_data.get('non_functional_segments', [])
    
    # Run the core optimization logic
    results = execute_module(train_data['trains'], non_functional_segments)
    
    # Update the live state in Firestore with the results
    update_and_get_dashboard_state(results, train_data['trains'])
    
    # Return the optimization results to the caller
    results.pop('solution', None) # The UI doesn't need the complex solution object
    return jsonify(results)

# ==============================================================================
# 2. Dashboard GET Endpoints
# ==============================================================================
# These endpoints allow the UI to fetch the specific data "classes" it needs.

<<<<<<< HEAD
    try:
        for tid, info in train_data.items():
            if 'delay_factors' in info and info['delay_factors']:
                info['delay_factors'] = DelayFactors(**info['delay_factors'])
            else:
                info['delay_factors'] = None
=======
@app.route('/dashboard/current_delays', methods=['GET'])
def get_current_delays():
    return jsonify(get_dashboard_data_class('currentDelays'))
>>>>>>> 85e58cc6b427e8889931461f0572eb93d128ccde

@app.route('/dashboard/train_queue', methods=['GET'])
def get_train_queue():
    return jsonify(get_dashboard_data_class('trainQueue'))

<<<<<<< HEAD
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid data format: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)

=======
@app.route('/dashboard/platform_status', methods=['GET'])
def get_platform_status():
    return jsonify(get_dashboard_data_class('platformStatus'))

@app.route('/dashboard/predicted_conflicts', methods=['GET'])
def get_predicted_conflicts():
    return jsonify(get_dashboard_data_class('predictedConflicts'))

@app.route('/dashboard/train_type_data', methods=['GET'])
def get_train_type_data():
    return jsonify(get_dashboard_data_class('trainTypeData'))
    
@app.route('/dashboard/audit_data', methods=['GET'])
def get_audit_data():
    return jsonify(get_dashboard_data_class('auditData'))

if __name__ == '__main__':
    # This allows you to run the server locally for testing
    app.run(debug=True, port=5000)
>>>>>>> 85e58cc6b427e8889931461f0572eb93d128ccde
