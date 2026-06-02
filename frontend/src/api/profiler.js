const API_BASE = "http://localhost:5000/api";

/**
 * POST /api/gather — kick off parallel OSINT modules.
 * Returns { session_id }.
 */
export async function startGathering(target, modules) {
  const res = await fetch(`${API_BASE}/gather`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...target, modules }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || `Server error ${res.status}`);
  }
  return res.json();
}

/**
 * GET /api/stream/:id — open an SSE connection.
 * onUpdate(payload) is called for each module event.
 * onComplete() is called when all modules finish.
 * Returns the EventSource so the caller can close it.
 */
export function streamResults(sessionId, onUpdate, onComplete) {
  const es = new EventSource(`${API_BASE}/stream/${sessionId}`);

  es.onmessage = (e) => {
    const payload = JSON.parse(e.data);
    if (payload.event === "complete") {
      onComplete();
      es.close();
    } else {
      onUpdate(payload);
    }
  };

  es.onerror = () => {
    es.close();
    onComplete();
  };

  return es;
}

/**
 * POST /api/analyze — send curated items to Claude for attack vector analysis.
 * Returns { analysis: string }.
 */
export async function analyzeData(targetInfo, curatedData, analysisType = "full", provider = "claude") {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target_info:   targetInfo,
      curated_data:  curatedData,
      analysis_type: analysisType,
      provider:      provider,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || `Analysis failed ${res.status}`);
  }
  return res.json();
}

/**
 * POST /api/score-email — score an email through SpamAssassin.
 * Returns { score, required, is_spam, verdict, rules, rule_summary }
 * or { error, raw?, stderr? } on failure.
 */
export async function scoreEmail(subject, body) {
  const res = await fetch(`${API_BASE}/score-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subject, body }),
  });
  return res.json();
}
