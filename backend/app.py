"""
UniThreat Backend API
=====================
Master's Thesis · Aarhus University · Security Research

Flask REST + Server-Sent Events (SSE) server that orchestrates all OSINT modules
and exposes their results to the React frontend.

Architecture
------------
Sessions are held in memory (dict).  Each session stores the target data, a
per-module results dict, and an event queue that is consumed by the SSE stream.

OSINT modules run in a background daemon thread.  As each module finishes it
appends an event to the queue; the SSE generator stream picks these up and
pushes them to the browser, enabling real-time progress without polling.

Endpoints
---------
POST /api/gather      — Start a gathering session; returns { session_id }
GET  /api/stream/:id  — SSE stream of { module, status, data } events
GET  /api/results/:id — Full results snapshot (polling fallback)
POST /api/analyze     — Forward curated data to Claude for threat analysis
GET  /health          — Health check
"""

import uuid
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# In-memory session store.  Not persisted across restarts.
# Structure: { session_id: { target, results, events, complete } }
sessions = {}


# ── Module loader ──────────────────────────────────────────────────────────

_MODULE_REGISTRY = {
    "google":          ("modules.search.google_module",           "GoogleModule"),
    "duckduckgo":      ("modules.search.duckduckgo_module",       "DuckDuckGoModule"),
    "github":          ("modules.social.github_module",           "GitHubModule"),
    "reddit":          ("modules.social.reddit_module",           "RedditModule"),
    "instagram":       ("modules.social.instagram_module",        "InstagramModule"),
    "username_enum":   ("modules.username.enumerator_module",     "UsernameEnumerator"),
    "email_osint":     ("modules.email_osint.hibp_module",        "EmailOsintModule"),
    "claude_research": ("modules.ai.claude_research_module",      "ClaudeResearchModule"),
}


def _get_module_class(module_id: str):
    """Dynamically import and return the class for a given module id."""
    if module_id not in _MODULE_REGISTRY:
        return None
    import importlib
    mod_path, cls_name = _MODULE_REGISTRY[module_id]
    return getattr(importlib.import_module(mod_path), cls_name)


def _push(session: dict, payload: dict) -> None:
    """Append a JSON-serialised event to the session event queue."""
    session["events"].append(json.dumps(payload))


def _run_modules(session_id: str, target: dict, modules_to_run: list) -> None:
    """Run OSINT modules concurrently and stream progress events via SSE."""
    session = sessions[session_id]

    def run_one(mod_key: str) -> None:
        Cls = _get_module_class(mod_key)
        if not Cls:
            return
        _push(session, {"module": mod_key, "status": "running"})
        try:
            result = Cls().run(target)
            session["results"][mod_key] = {"status": "done", "data": result}
            _push(session, {"module": mod_key, "status": "done", "data": result})
        except Exception as exc:
            err = {"error": str(exc), "trace": traceback.format_exc()}
            session["results"][mod_key] = {"status": "error", "data": err}
            _push(session, {"module": mod_key, "status": "error", "data": err})

    with ThreadPoolExecutor(max_workers=len(modules_to_run) or 1) as pool:
        pool.map(run_one, modules_to_run)

    session["complete"] = True
    _push(session, {"event": "complete"})


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/api/gather", methods=["POST"])
def gather():
    """
    Start a new OSINT gathering session.

    Request body (JSON):
        name     (str, required) — Target full name
        username (str, optional) — Social media handle
        email    (str, optional) — Email address
        modules  (list, optional) — Module ids to run (default: duckduckgo, github, reddit)

    Returns:
        200 { session_id: str } — Use this id to connect the SSE stream.
        400 { error: str }      — Missing required field.
    """
    data = request.get_json()
    if not data or not data.get("name", "").strip():
        return jsonify({"error": "Missing required field: 'name'"}), 400

    session_id = str(uuid.uuid4())
    target = {
        "name":     data["name"].strip(),
        "username": data.get("username", "").strip(),
        "email":    data.get("email", "").strip(),
    }
    modules_to_run = data.get("modules", ["duckduckgo", "github", "reddit"])

    sessions[session_id] = {
        "target":   target,
        "results":  {},
        "events":   [],
        "complete": False,
    }

    threading.Thread(
        target=_run_modules,
        args=(session_id, target, modules_to_run),
        daemon=True,
    ).start()

    return jsonify({"session_id": session_id}), 200


@app.route("/api/stream/<session_id>")
def stream(session_id: str):
    """
    Open a Server-Sent Events stream for a gathering session.

    The generator polls the session event queue and yields new events as they
    arrive.  The stream closes automatically when the session is complete.

    Args:
        session_id: UUID returned by POST /api/gather.

    Returns:
        200 text/event-stream — SSE stream of { module, status, data } objects.
        404 { error }         — Session not found.
    """
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    def generate():
        session = sessions[session_id]
        cursor  = 0
        while True:
            while cursor < len(session["events"]):
                yield f"data: {session['events'][cursor]}\n\n"
                cursor += 1
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
    """
    Return the full results snapshot for a session.

    Useful as a polling fallback if SSE is not supported by the client.

    Args:
        session_id: UUID returned by POST /api/gather.

    Returns:
        200 { target, results, complete } — Full session state.
        404 { error }                     — Session not found.
    """
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    s = sessions[session_id]
    return jsonify({"target": s["target"], "results": s["results"], "complete": s["complete"]})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Forward curated OSINT data to the AI analyser for threat assessment.

    Request body (JSON):
        target_info   (dict) — { name, username, email }
        curated_data  (list) — List of { id, module, label, content } items
        analysis_type (str)  — "full" | "phishing" | "social_engineering"

    Returns:
        200 { analysis: str } — Markdown threat assessment from Claude.
        500 { error, trace }  — Unexpected error from the AI module.
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
        )
        return jsonify({"analysis": result})
    except Exception as exc:
        import traceback
        return jsonify({"error": str(exc), "trace": traceback.format_exc()}), 500


@app.route("/health")
def health():
    """Simple health check used by monitoring and the start script."""
    return jsonify({"status": "healthy", "version": "2.0"})


if __name__ == "__main__":
    app.run(port=5000, debug=True, threaded=True)
