/**
 * TargetDossier.jsx — Right dock
 *
 * Top: Overview map of the whole graph.
 * Below, four tabs:
 *   - Detail view     : properties of the selected entity
 *   - Intel workspace : where the analyst builds the intelligence brief
 *       1. Pinned results — entities pinned from the graph or list
 *       2. Analyst notes  — free-text for manual findings
 *       3. Analysis type  — scope selector sent to the AI
 *       4. Generate       — triggers the Claude threat assessment
 *       5. AI output      — the structured analysis result
 *   - Spam checker    : SpamAssassin email scoring
 *   - Help            : how to run the app, and usage tips
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
 *   activeTab            {string}   - "detail" | "intel" | "spam" | "help"
 *   onTabChange          {Function} - Switches the visible tab
 *   helpTopic            {string}   - "run" | "tips"
 *   onHelpTopicChange    {Function} - Switches the visible help topic
 *   selectedNode         {object}   - Node selected on the graph, or null
 *   onPinToggle          {Function} - Pin or unpin the selected entity
 *   onExpand             {Function} - Expand a module's collection
 *   overview             {node}     - The rendered Overview map
 *   hidden               {boolean}  - Hides the dock but keeps its state
 */

import { useState } from "react";
import SpamChecker from "./SpamChecker";
import DetailView from "./DetailView";
import HelpPanel from "./HelpPanel";

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
    sections.push({ title: "Analysis", body: text.trim() });
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
  activeTab,
  onTabChange,
  helpTopic,
  onHelpTopicChange,
  selectedNode,
  onPinToggle,
  onExpand,
  overview,
  hidden,
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!analysis) return;
    navigator.clipboard.writeText(analysis).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const sections    = parseAnalysis(analysis);
  const canGenerate = (pinnedItems.length > 0 || notes.trim().length > 0) && !isAnalyzing;
  const selectedPinned = !!selectedNode?.item && pinnedItems.some((p) => p.id === selectedNode.item.id);

  return (
    <aside className={`dock ${hidden ? "is-hidden" : ""}`}>
      <section className="dock-overview" aria-label="Overview">
        <h2 className="panel-title">Overview</h2>
        <div className="overview-frame">{overview}</div>
      </section>

      <div className="dock-tabs" role="tablist" aria-label="Details">
        {[
          { id: "detail", label: "Detail view" },
          { id: "intel",  label: `Intel workspace${pinnedItems.length ? ` (${pinnedItems.length})` : ""}` },
          { id: "spam",   label: "Spam checker" },
          { id: "help",   label: "Help" },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`dock-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Detail tab */}
      {activeTab === "detail" && (
        <div className="dossier-scroll">
          <DetailView node={selectedNode} isPinned={selectedPinned} onPinToggle={onPinToggle} onExpand={onExpand} />
        </div>
      )}

      {/* Spam Checker tab — hidden rather than removed so a drafted email survives tab changes */}
      <div className={`dossier-scroll ${activeTab === "spam" ? "" : "is-hidden"}`}>
        <SpamChecker />
      </div>

      {/* Help tab */}
      {activeTab === "help" && (
        <div className="dossier-scroll">
          <HelpPanel topic={helpTopic} onTopicChange={onHelpTopicChange} />
        </div>
      )}

      {/* Scrollable workspace content — Intel tab */}
      {activeTab === "intel" && (
      <div className="dossier-scroll">

        <div className="workspace-target">
          {target?.name
            ? <strong>{target.name}</strong>
            : <span className="dim">No target loaded</span>}
          {target?.username && <span className="dim">@{target.username.replace(/^@/, "")}</span>}
          {target?.email    && <span className="dim">{target.email}</span>}
        </div>

        {/* ── 1. Pinned results ── */}
        <div className="workspace-section">
          <h2 className="panel-title">Pinned intel ({pinnedItems.length})</h2>
          {pinnedItems.length === 0 ? (
            <div className="panel-empty boxed">
              Select an entity, then pin it. Pinned entities are included in the analysis.
            </div>
          ) : (
            <div className="pinned-list">
              {pinnedItems.map((item) => (
                <div key={item.id} className="pinned-chip">
                  <div className="pinned-chip-text">
                    <div className="pinned-chip-title">{item.title}</div>
                    <div className="pinned-chip-meta">{item.category}</div>
                  </div>
                  <button
                    type="button"
                    className="unpin-btn"
                    onClick={() => onUnpin(item)}
                    aria-label={`Remove ${item.title} from workspace`}
                    title="Remove from workspace"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── 2. Analyst notes ── */}
        <div className="workspace-section">
          <label className="panel-title" htmlFor="analyst-notes">Analyst notes</label>
          <textarea
            id="analyst-notes"
            className="workspace-textarea"
            rows={5}
            placeholder={"Add manual findings, extra context,\nphone numbers, physical locations…"}
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
          />
        </div>

        {/* ── 3. Analysis type + Generate ── */}
        <div className="workspace-section">
          <label className="panel-title" htmlFor="analysis-type">Attack vector analysis</label>
          <select
            id="analysis-type"
            className="analysis-type-select"
            value={analysisType}
            onChange={(e) => onAnalysisTypeChange(e.target.value)}
          >
            <option value="full">Full assessment</option>
            <option value="phishing">Phishing focus</option>
            <option value="social_engineering">Social engineering focus</option>
          </select>
          <button
            type="button"
            className="generate-btn"
            onClick={onGenerate}
            disabled={!canGenerate}
          >
            {isAnalyzing
              ? "Analyzing…"
              : `Generate attack vectors (${pinnedItems.length} pinned)`}
          </button>
        </div>

        {/* ── 4. Loading spinner ── */}
        {isAnalyzing && (
          <div className="analyzing">
            <div className="spinner-ring" />
            <span>Analyzing with AI</span>
          </div>
        )}

        {/* ── 5. AI output ── */}
        {!isAnalyzing && analysis && (
          <div className="workspace-section">
            <h2 className="panel-title">AI output</h2>
            <div className="analysis-out">
              {sections.map((sec, i) => (
                <div key={i} className="analysis-section">
                  <div className="analysis-section-title">{sec.title}</div>
                  <div className="analysis-section-body">{sec.body}</div>
                </div>
              ))}
            </div>
            <button type="button" className="secondary-btn" onClick={handleCopy}>
              {copied ? "Copied" : "Copy full analysis"}
            </button>
          </div>
        )}

      </div>
      )}
    </aside>
  );
}
