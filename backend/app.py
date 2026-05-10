# UniThreat Backend
# Flask server that runs OSINT modules and streams results to the React frontend.
# Each search session gets a unique ID so multiple users could run at the same time.

import uuid
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow the React frontend (localhost:5173) to call this API

# All active sessions are stored here in memory.
# Each session holds the target info, results from each module, and a list of events
# that get streamed to the frontend in real time.
sessions = {}

# Registry of all available OSINT modules.
# Key = module ID used in the frontend, Value = (python module path, class name)
_MODULE_REGISTRY = {
    "google":          ("modules.search.google_module",      "GoogleModule"),
    "duckduckgo":      ("modules.search.duckduckgo_module",  "DuckDuckGoModule"),
    "instagram":       ("modules.social.instagram_module",   "InstagramModule"),
    "linkedin":        ("modules.social.linkedin_module",    "LinkedInModule"),
    "username_enum":   ("modules.username.enumerator_module","UsernameEnumerator"),
    "email_osint":     ("modules.email_osint.hibp_module",   "EmailOsintModule"),
    "claude_research": ("modules.ai.claude_research_module", "ClaudeResearchModule"),
}


def _get_module_class(module_id: str):
    """Dynamically import and return the class for a module ID."""
    if module_id not in _MODULE_REGISTRY:
        return None
    import importlib
    mod_path, cls_name = _MODULE_REGISTRY[module_id]
    return getattr(importlib.import_module(mod_path), cls_name)


def _push(session: dict, payload: dict) -> None:
    """Append an event to the session queue so the SSE stream can pick it up."""
    session["events"].append(json.dumps(payload))


def _run_modules(session_id: str, target: dict, modules_to_run: list) -> None:
    """Run all selected OSINT modules in parallel threads and push progress events."""
    session = sessions[session_id]

    def run_one(mod_key: str) -> None:
        # Tell the frontend this module has started
        _push(session, {"module": mod_key, "status": "running"})
        try:
            Cls = _get_module_class(mod_key)
            if not Cls:
                return
            result = Cls().run(target)
            session["results"][mod_key] = {"status": "done", "data": result}
            _push(session, {"module": mod_key, "status": "done", "data": result})
        except Exception as exc:
            # Capture the full stack trace so it shows in the UI error card
            err = {"error": str(exc), "trace": traceback.format_exc()}
            session["results"][mod_key] = {"status": "error", "data": err}
            _push(session, {"module": mod_key, "status": "error", "data": err})

    # Run all modules at the same time instead of one by one
    with ThreadPoolExecutor(max_workers=len(modules_to_run) or 1) as pool:
        pool.map(run_one, modules_to_run)

    session["complete"] = True
    _push(session, {"event": "complete"})


# ── API Routes ─────────────────────────────────────────────────────────────────

@app.route("/api/gather", methods=["POST"])
def gather():
    """
    Start a new OSINT session.

    Body: { name, username?, email?, modules?: [list of module IDs] }
    Returns: { session_id }
    """
    data = request.get_json()
    if not data or not data.get("name", "").strip():
        return jsonify({"error": "Missing required field: 'name'"}), 400

    session_id = str(uuid.uuid4())
    target = {
        "name":         data["name"].strip(),
        "username":     data.get("username", "").strip(),
        "email":        data.get("email", "").strip(),
        "linkedin_url": data.get("linkedin_url", "").strip(),
    }
    modules_to_run = data.get("modules", ["duckduckgo", "claude_research"])

    sessions[session_id] = {
        "target":   target,
        "results":  {},
        "events":   [],
        "complete": False,
    }

    # Run modules in a background thread so the HTTP response returns immediately
    threading.Thread(
        target=_run_modules,
        args=(session_id, target, modules_to_run),
        daemon=True,
    ).start()

    return jsonify({"session_id": session_id}), 200


@app.route("/api/stream/<session_id>")
def stream(session_id: str):
    """
    Server-Sent Events stream for a session.
    The frontend connects here and receives module updates in real time.
    """
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    def generate():
        session = sessions[session_id]
        cursor = 0
        while True:
            # Send any new events that arrived since our last check
            while cursor < len(session["events"]):
                yield f"data: {session['events'][cursor]}\n\n"
                cursor += 1
            # Stop the stream once all modules have finished
            if session["complete"] and cursor >= len(session["events"]):
                break
            time.sleep(0.3)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/results/<session_id>")
def get_results(session_id: str):
    """Polling fallback — returns the full results snapshot for a session."""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    s = sessions[session_id]
    return jsonify({"target": s["target"], "results": s["results"], "complete": s["complete"]})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Send the analyst's curated OSINT data to Claude for threat analysis.

    Body: { target_info, curated_data, analysis_type }
    Returns: { analysis: markdown string }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    try:
        from ai.analyzer import AttackVectorAnalyzer
        result = AttackVectorAnalyzer().analyze(
            target_info=data.get("target_info", {}),
            curated_data=data.get("curated_data", []),
            analysis_type=data.get("analysis_type", "full"),
            provider=data.get("provider", "claude"),
        )
        return jsonify({"analysis": result})
    except Exception as exc:
        return jsonify({"error": str(exc), "trace": traceback.format_exc()}), 500


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": "2.0"})


if __name__ == "__main__":
    app.run(port=5000, debug=True, threaded=True)
