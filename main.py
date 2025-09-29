from flask import Flask, request, jsonify
from flask_cors import CORS  # Import the CORS library
from or_module import execute_module, DelayFactors
from datetime import datetime

app = Flask(__name__)
# Explicitly allow all origins ('*') to access all routes
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/optimize', methods=['POST'])
def run_optimization():
    """
    API endpoint to run the train scheduling optimization.
    Expects a JSON payload with train data.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    train_data = data.get('trains')
    non_functional = data.get('non_functional_segments', [])

    if not train_data:
        return jsonify({"error": "Missing 'trains' data in request body"}), 400

    try:
        for tid, info in train_data.items():
            if 'delay_factors' in info and info['delay_factors']:
                info['delay_factors'] = DelayFactors(**info['delay_factors'])
            else:
                info['delay_factors'] = None

        results = execute_module(train_data, non_functional)
        return jsonify(results)

    except (TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid data format: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)

