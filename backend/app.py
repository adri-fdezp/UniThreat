from flask import Flask, request, jsonify
from flask_cors import CORS

# Import our modular business logic
from risk_profiling.profiler import RiskProfiler
from search_engines.google_engine import GoogleSearch

app = Flask(__name__)

# Enable CORS so the React frontend can communicate with this API
CORS(app)

@app.route('/api/profile', methods=['POST'])
def generate_profile():
    """
    Main endpoint for triggering an OSINT profile scan.
    Receives: JSON { "name": "Target Name" }
    Returns: Comprehensive JSON report of findings.
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Missing 'name' in request body"}), 400
    
    target_name = data['name']
    selected_modules = data.get('modules', [])
    
    try:
        # Initialize the profiler coordinator
        profiler = RiskProfiler()
        
        # Add the Google Search module
        profiler.add_engine(GoogleSearch(headless=False))
        
        # Execute with filtered modules
        report = profiler.profile(target_name, selected_modules=selected_modules)
        
        return jsonify(report), 200

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"[CRITICAL ERROR] API Failed: {e}")
        print(error_msg)
        return jsonify({"error": str(e), "traceback": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple heart-beat endpoint to verify server availability."""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Run the server on the default Flask port
    app.run(port=5000, debug=True)