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
  const barFilled = hasScore ? Math.min(Math.round(result.score), BAR_MAX) : 0;
  const barEmpty  = Math.max(0, BAR_MAX - barFilled);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, padding: "10px 12px" }}>

      {/* Subject */}
      <div>
        <div style={labelStyle}>SUBJECT</div>
        <input
          style={inputStyle}
          placeholder="Email subject line"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
        />
      </div>

      {/* Body */}
      <div>
        <div style={labelStyle}>BODY</div>
        <textarea
          className="workspace-textarea"
          rows={12}
          placeholder={"Paste the full email body here…"}
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </div>

      <button
        className="generate-btn"
        onClick={handleScore}
        disabled={!canScore}
      >
        {loading ? "SCORING…" : "SCORE EMAIL"}
      </button>

      {/* Error state */}
      {hasError && (
        <div className="error-banner" style={{ fontSize: 10 }}>
          <strong>SpamAssassin error:</strong> {result.error}
          {result.stderr && (
            <div style={{ marginTop: 6, color: "var(--text-dim)", fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
              stderr: {result.stderr}
            </div>
          )}
          {result.raw && (
            <details style={{ marginTop: 6 }}>
              <summary style={{ cursor: "pointer", color: "var(--text-dim)" }}>Raw SA output</summary>
              <pre style={{ fontSize: 9, overflowX: "auto", marginTop: 4, whiteSpace: "pre-wrap" }}>
                {result.raw}
              </pre>
            </details>
          )}
        </div>
      )}

      {/* Score result */}
      {hasScore && (
        <div style={resultBoxStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: result.is_spam ? "var(--red)" : "var(--green)" }}>
              {result.verdict}
            </span>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--accent)", fontFamily: "monospace" }}>
              {result.score.toFixed(1)} / {result.required.toFixed(1)}
            </span>
          </div>

          <div style={{ fontFamily: "monospace", fontSize: 10, color: result.is_spam ? "var(--red)" : "var(--text-dim)", marginBottom: 10 }}>
            {"█".repeat(barFilled)}{"░".repeat(barEmpty)}
          </div>

          {/* Detailed per-rule table (when SpamAssassin provides X-Spam-Report) */}
          {result.detailed_rules?.length > 0 ? (
            <>
              <div style={labelStyle}>TRIGGERED RULES</div>
              <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 6, fontSize: 9, fontFamily: "monospace" }}>
                <thead>
                  <tr>
                    <th style={thStyle}>SCORE</th>
                    <th style={{ ...thStyle, textAlign: "left" }}>RULE</th>
                    <th style={{ ...thStyle, textAlign: "left" }}>DESCRIPTION</th>
                  </tr>
                </thead>
                <tbody>
                  {result.detailed_rules.map((r, i) => (
                    <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ ...tdStyle, textAlign: "right", color: r.score > 0 ? "var(--red)" : r.score < 0 ? "var(--green)" : "var(--text-dim)" }}>
                        {r.score > 0 ? `+${r.score.toFixed(1)}` : r.score.toFixed(1)}
                      </td>
                      <td style={{ ...tdStyle, color: "var(--accent)", whiteSpace: "nowrap" }}>{r.name}</td>
                      <td style={{ ...tdStyle, color: "var(--text-dim)" }}>{r.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : result.rules?.length > 0 && (
            <>
              <div style={labelStyle}>TRIGGERED RULES</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                {result.rules.map((rule) => (
                  <span key={rule} style={ruleChipStyle}>{rule}</span>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

const labelStyle = {
  fontSize: 9,
  color: "var(--text-dim)",
  fontWeight: 600,
  letterSpacing: 1,
  textTransform: "uppercase",
  marginBottom: 4,
};

const inputStyle = {
  width: "100%",
  padding: "6px 8px",
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: 4,
  color: "var(--text)",
  fontFamily: "inherit",
  fontSize: 11,
};

const resultBoxStyle = {
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: 4,
  padding: "10px 12px",
};

const ruleChipStyle = {
  fontSize: 9,
  fontFamily: "monospace",
  background: "var(--bg-main)",
  border: "1px solid var(--border)",
  borderRadius: 3,
  padding: "2px 5px",
  color: "var(--text-dim)",
};

const thStyle = {
  padding: "3px 8px 5px",
  color: "var(--text-dim)",
  fontWeight: 700,
  letterSpacing: 1,
  fontSize: 8,
  textAlign: "right",
  borderBottom: "1px solid var(--border)",
};

const tdStyle = {
  padding: "4px 8px",
  verticalAlign: "top",
};
