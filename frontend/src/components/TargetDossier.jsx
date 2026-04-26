/**
 * TargetDossier.jsx — Intel Workspace (right sidebar)
 *
 * The workspace is where the analyst builds the intelligence brief:
 *   1. Pinned results — cards pinned from the centre panel
 *   2. Analyst notes  — free-text for manual findings
 *   3. Analysis type  — scope selector sent to the AI
 *   4. Generate       — triggers the Claude threat assessment
 *   5. AI output      — the structured analysis result
 *
 * Props:
 *   target               {object}   - { name, username, email }
 *   pinnedItems          {Array}    - Cards pinned by the analyst
 *   onUnpin              {Function} - Remove an item from pinnedItems
 *   notes                {string}   - Free-text notes value
 *   onNotesChange        {Function} - Notes onChange handler
 *   analysisType         {string}   - "full" | "phishing" | "social_engineering"
 *   onAnalysisTypeChange {Function} - Analysis type onChange handler
 *   onGenerate           {Function} - Triggers the AI analysis
 *   isAnalyzing          {boolean}  - True while waiting for the AI response
 *   analysis             {string}   - Raw markdown text returned by Claude
 */

import { useState } from "react";

/**
 * Split Claude's markdown response on ## headers into labelled sections.
 * Falls back to a single block if no headers are present.
 *
 * @param {string} text - Raw analysis markdown
 * @returns {Array<{title: string, body: string}>}
 */
function parseAnalysis(text) {
  if (!text) return [];
  const sections = [];
  text.split(/^##\s+/m).forEach((part) => {
    const nl = part.indexOf("\n");
    if (nl === -1) return;
    const title = part.slice(0, nl).trim();
    const body  = part.slice(nl + 1).trim();
    if (title) sections.push({ title, body });
  });
  if (sections.length === 0 && text.trim())
    sections.push({ title: "ANALYSIS", body: text.trim() });
  return sections;
}

export default function TargetDossier({
  target,
  pinnedItems,
  onUnpin,
  notes,
  onNotesChange,
  analysisType,
  onAnalysisTypeChange,
  onGenerate,
  isAnalyzing,
  analysis,
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!analysis) return;
    navigator.clipboard.writeText(analysis).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const sections   = parseAnalysis(analysis);
  const canGenerate = (pinnedItems.length > 0 || notes.trim().length > 0) && !isAnalyzing;

  return (
    <aside className="notes-sidebar">

      {/* Fixed header — target identity summary */}
      <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
        <label className="section-label" style={{ marginBottom: target?.name ? 4 : 0 }}>
          INTEL WORKSPACE
        </label>
        {target?.name
          ? <div style={{ fontSize: 12, fontWeight: 700, color: "var(--accent)" }}>{target.name}</div>
          : <div style={{ fontSize: 10, color: "var(--text-dim)" }}>No target loaded</div>
        }
        {target?.username && <div style={{ fontSize: 10, color: "var(--text-dim)" }}>@{target.username}</div>}
        {target?.email    && <div style={{ fontSize: 10, color: "var(--text-dim)" }}>{target.email}</div>}
      </div>

      {/* Scrollable workspace content */}
      <div className="dossier-scroll">

        {/* ── 1. Pinned results ── */}
        <div className="workspace-section">
          <label className="section-label">PINNED INTEL ({pinnedItems.length})</label>
          {pinnedItems.length === 0 ? (
            <div className="empty-workspace">
              Pin results from the centre panel using ⊕.<br />
              Pinned items are included in the AI analysis.
            </div>
          ) : (
            <div className="pinned-list">
              {pinnedItems.map((item) => (
                <div key={item.id} className="pinned-chip">
                  <div className="pinned-chip-text">
                    <div className="pinned-chip-title">{item.title}</div>
                    <div className="pinned-chip-meta">
                      [{item.module.toUpperCase()}] {item.category}
                    </div>
                  </div>
                  <button
                    className="unpin-btn"
                    onClick={() => onUnpin(item)}
                    title="Remove from workspace"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <hr className="panel-divider" />

        {/* ── 2. Analyst notes ── */}
        <div className="workspace-section">
          <label className="section-label">ANALYST NOTES</label>
          <textarea
            className="workspace-textarea"
            rows={5}
            placeholder={"Add manual findings, extra context,\nphone numbers, physical locations…"}
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
          />
        </div>

        <hr className="panel-divider" />

        {/* ── 3. Analysis type + Generate ── */}
        <div className="workspace-section">
          <label className="section-label">ATTACK VECTOR ANALYSIS</label>
          <select
            className="analysis-type-select"
            value={analysisType}
            onChange={(e) => onAnalysisTypeChange(e.target.value)}
            style={{ marginBottom: 8 }}
          >
            <option value="full">Full Threat Assessment</option>
            <option value="phishing">Phishing Focus</option>
            <option value="social_engineering">Social Engineering</option>
          </select>
          <button
            className="generate-btn"
            onClick={onGenerate}
            disabled={!canGenerate}
          >
            {isAnalyzing
              ? "ANALYZING…"
              : `GENERATE ATTACK VECTORS (${pinnedItems.length} pinned)`}
          </button>
        </div>

        {/* ── 4. Loading spinner ── */}
        {isAnalyzing && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "16px 0" }}>
            <div className="spinner-ring" />
            <span style={{ fontSize: 10, color: "var(--text-dim)", fontWeight: 700, letterSpacing: 1 }}>
              ANALYZING WITH AI
            </span>
          </div>
        )}

        {/* ── 5. AI output ── */}
        {!isAnalyzing && analysis && (
          <div className="workspace-section">
            <label className="section-label">AI OUTPUT</label>
            <div className="analysis-out">
              {sections.map((sec, i) => (
                <div key={i} className="analysis-section">
                  <div className="analysis-section-title">{sec.title.toUpperCase()}</div>
                  <div className="analysis-section-body">{sec.body}</div>
                </div>
              ))}
            </div>
            <button className="copy-btn" style={{ marginTop: 8 }} onClick={handleCopy}>
              {copied ? "✓ COPIED" : "COPY FULL ANALYSIS"}
            </button>
          </div>
        )}

      </div>
    </aside>
  );
}
