/**
 * ProfileResults.jsx — Centre panel result display
 *
 * Renders all OSINT results as individual cards, one per hit.
 * Provides a text filter so the analyst can quickly find relevant items.
 * Each card has a pin button that adds it to the Intel Workspace.
 *
 * Props:
 *   flatResults  {Array}    - All flattened result items from all modules
 *   pinnedItems  {Array}    - Currently pinned items (used to mark cards)
 *   onPinToggle  {Function} - Called with an item to pin or unpin it
 *   isGathering  {boolean}  - True while modules are still running
 */

import { useState, useMemo } from "react";

// Human-readable labels for the module badge on each card
const MODULE_LABELS = {
  google:          "GOOGLE",
  duckduckgo:      "DDGO",
  github:          "GITHUB",
  reddit:          "REDDIT",
  instagram:       "INSTAGRAM",
  username_enum:   "USERNAME",
  email_osint:     "EMAIL",
  claude_research: "CLAUDE AI",
};

// ── ResultCard ─────────────────────────────────────────────────────────────
/**
 * A single result card.  Shows module badge, category, title, URL, and a
 * short content preview.  The pin button toggles the card in the workspace.
 */
function ResultCard({ item, isPinned, onPinToggle }) {
  return (
    <div className={`result-card ${isPinned ? "pinned" : ""}`}>
      <div className="result-card-main">

        {/* Source badge + category label */}
        <div className="result-card-meta">
          <span className={`result-module-badge ${item.module}`}>
            {MODULE_LABELS[item.module] || item.module.toUpperCase()}
          </span>
          <span className="result-category">{item.category}</span>
        </div>

        {/* Title — always single line, truncated */}
        <div className="result-card-title">{item.title}</div>

        {/* Clickable URL */}
        {item.url && (
          <a
            className="result-card-url"
            href={item.url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            {item.url}
          </a>
        )}

        {/* Content preview — clamped to 3 lines */}
        {item.content && (
          <div className="result-card-desc">{item.content}</div>
        )}
      </div>

      {/* Pin / unpin button */}
      <button
        className={`pin-btn ${isPinned ? "pinned-btn" : ""}`}
        onClick={() => onPinToggle(item)}
        title={isPinned ? "Remove from workspace" : "Add to workspace"}
      >
        {isPinned ? "📌" : "⊕"}
      </button>
    </div>
  );
}

// ── ProfileResults ─────────────────────────────────────────────────────────
export default function ProfileResults({ flatResults, pinnedItems, onPinToggle, isGathering }) {
  const [filterText, setFilterText] = useState("");

  // Filter by text across title, category, content, and URL
  const filtered = useMemo(() => {
    if (!filterText.trim()) return flatResults;
    const q = filterText.toLowerCase();
    return flatResults.filter(
      (r) =>
        r.title.toLowerCase().includes(q)    ||
        r.category.toLowerCase().includes(q) ||
        r.content.toLowerCase().includes(q)  ||
        r.url.toLowerCase().includes(q)
    );
  }, [flatResults, filterText]);

  return (
    <>
      {/* Toolbar: text filter + result count */}
      <div className="results-toolbar">
        <input
          className="filter-input"
          placeholder="Filter results by keyword…"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
        />
        <span className="result-count">
          {isGathering && (
            <span style={{ color: "var(--yellow)", marginRight: 5 }}>●</span>
          )}
          {filtered.length} / {flatResults.length} results
        </span>
      </div>

      {/* Scrollable card list */}
      <div className="results-scroll">
        {filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-dim)", fontSize: 11 }}>
            {flatResults.length === 0
              ? "Waiting for results…"
              : "No results match the current filter."}
          </div>
        )}

        {filtered.map((item) => (
          <ResultCard
            key={item.id}
            item={item}
            isPinned={pinnedItems.some((p) => p.id === item.id)}
            onPinToggle={onPinToggle}
          />
        ))}
      </div>
    </>
  );
}
