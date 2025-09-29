from flask import Flask, request, jsonify
from or_module import execute_module, DelayFactors  # Import your main logic
from datetime import datetime

app = Flask(__name__)

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
        # The 'delay_factors' part is optional in the JSON payload
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
        # A general error handler for unexpected issues
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

if __name__ == '__main__':
    # Runs the Flask app on http://127.0.0.1:5000
    app.run(debug=True)
