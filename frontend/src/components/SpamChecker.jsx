import { useState } from "react";
import { scoreEmail } from "../api/profiler";

const BAR_MAX = 20;

export default function SpamChecker() {
  const [subject, setSubject] = useState("");
  const [body,    setBody]    = useState("");
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);

  const handleScore = async () => {
    setLoading(true);
    setResult(null);
    const data = await scoreEmail(subject, body);
    setResult(data);
    setLoading(false);
  };

  const canScore  = !loading && (subject.trim() || body.trim());
  const hasError  = result && result.error;
  const hasScore  = result && result.score != null;
  const barWidth  = hasScore ? Math.max(0, Math.min(result.score / BAR_MAX, 1)) * 100 : 0;

  return (
    <div className="spam-checker">

      {/* Subject */}
      <div className="workspace-section">
        <label className="panel-title" htmlFor="spam-subject">Subject</label>
        <input
          id="spam-subject"
          className="input-field"
          placeholder="Email subject line"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
        />
      </div>

      {/* Body */}
      <div className="workspace-section">
        <label className="panel-title" htmlFor="spam-body">Body</label>
        <textarea
          id="spam-body"
          className="workspace-textarea"
          rows={10}
          placeholder={"Paste the full email body here…"}
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </div>

      <button
        type="button"
        className="generate-btn"
        onClick={handleScore}
        disabled={!canScore}
      >
        {loading ? "Scoring…" : "Score email"}
      </button>

      {/* Error state */}
      {hasError && (
        <div className="error-banner in-panel">
          <strong>SpamAssassin error:</strong> {result.error}
          {result.stderr && <div className="spam-stderr">stderr: {result.stderr}</div>}
          {result.raw && (
            <details className="spam-raw">
              <summary>Raw SpamAssassin output</summary>
              <pre>{result.raw}</pre>
            </details>
          )}
        </div>
      )}

      {/* Score result */}
      {hasScore && (
        <div className="spam-result">
          <div className="spam-verdict">
            <span className={result.is_spam ? "text-red" : "text-green"}>{result.verdict}</span>
            <span className="spam-score">{result.score.toFixed(1)} / {result.required.toFixed(1)}</span>
          </div>

          <div className="score-meter" aria-hidden="true">
            <div className={`score-meter-fill ${result.is_spam ? "spam" : ""}`} style={{ width: `${barWidth}%` }} />
          </div>

          {/* Detailed per-rule table (when SpamAssassin provides X-Spam-Report) */}
          {result.detailed_rules?.length > 0 ? (
            <>
              <h2 className="panel-title">Triggered rules</h2>
              <table className="rule-table">
                <thead>
                  <tr>
                    <th scope="col" className="num">Score</th>
                    <th scope="col">Rule</th>
                    <th scope="col">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {result.detailed_rules.map((r, i) => (
                    <tr key={i}>
                      <td className={`num ${r.score > 0 ? "text-red" : r.score < 0 ? "text-green" : "dim"}`}>
                        {r.score > 0 ? `+${r.score.toFixed(1)}` : r.score.toFixed(1)}
                      </td>
                      <td className="rule-name">{r.name}</td>
                      <td className="dim">{r.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : result.rules?.length > 0 && (
            <>
              <h2 className="panel-title">Triggered rules</h2>
              <div className="rule-chips">
                {result.rules.map((rule) => (
                  <span key={rule} className="rule-chip">{rule}</span>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
