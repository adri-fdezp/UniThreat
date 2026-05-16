/**
 * App.jsx — Root component for UniThreat
 *
 * Manages the three-panel layout and all top-level application state:
 *   - LEFT SIDEBAR  : target form, module selection, live module status
 *   - CENTRE PANEL  : individual OSINT result cards (streamed in real time)
 *   - RIGHT SIDEBAR : Intel Workspace — pinned cards, analyst notes, AI output
 *
 * Workflow:
 *   1. User fills in the target and selects modules → clicks EXECUTE
 *   2. Backend runs modules in parallel and streams progress via SSE
 *   3. Results are flattened into individual cards as each module completes
 *   4. User pins relevant cards to the right workspace
 *   5. User adds analyst notes, selects analysis type, clicks GENERATE
 *   6. Claude analyses the pinned data and returns a structured threat report
 */

import { useState, useRef } from "react";
import { startGathering, streamResults, analyzeData } from "./api/profiler";
import Header        from "./components/Header";
import SearchForm    from "./components/SearchForm";
import ProfileResults from "./components/ProfileResults";
import TargetDossier from "./components/TargetDossier";
import "./styles/App.css";

// ── Module registry ────────────────────────────────────────────────────────
// Add new OSINT modules here.  The id must match the backend module key.
const ALL_MODULES = [
  { id: "google",          label: "GOOGLE",          note: "Selenium — visible browser, manual CAPTCHA if needed" },
  { id: "duckduckgo",      label: "DUCKDUCKGO",      note: "Fast API-based web dorks (15+ query templates)" },
  { id: "instagram",       label: "INSTAGRAM",       note: "Public profile and recent posts (requires username)" },
  { id: "linkedin",        label: "LINKEDIN",        note: "Full profile scrape — requires LinkedIn URL and credentials in .env" },
  { id: "username_enum",   label: "USERNAME",        note: "500+ site enumeration via WhatsMyName dataset" },
  { id: "email_osint",     label: "EMAIL OSINT",     note: "Gravatar lookup + Holehe site registrations" },
  { id: "claude_research", label: "CLAUDE RESEARCH", note: "AI-driven OSINT profile — identity, presence, search queries" },
  { id: "gemini_research", label: "GEMINI RESEARCH", note: "AI-driven OSINT profile via Google Gemini — identity, presence, search queries" },
];

// ── Data flattener ─────────────────────────────────────────────────────────
/**
 * Converts raw module output into a flat array of individual result items.
 *
 * Each item has a consistent shape so the UI can render all sources uniformly:
 *   { id, module, category, title, url, content }
 *
 * @param {string} moduleId - The module identifier (e.g. "github")
 * @param {object} data     - Raw data object returned by the backend module
 * @returns {Array<object>} Flat list of result items
 */
function flattenModuleData(moduleId, data) {
  const items = [];
  if (!data || data.error) return items;

  let seq = 0;
  const push = (category, title, url, content) =>
    items.push({
      id:       `${moduleId}_${seq++}`,
      module:   moduleId,
      category: category || "",
      title:    title    || "(no title)",
      url:      url      || "",
      content:  content  || "",
    });

  switch (moduleId) {
    // Google and DuckDuckGo share the same flat structure — one card per hit
    case "google":
    case "duckduckgo": {
      (data.results || []).forEach((r) => {
        if (!r.error) push(r.category || "Search", r.title, r.url, r.description);
      });
      break;
    }

    case "instagram": {
      push(
        "Profile",
        `Instagram: @${data.username}`,
        `https://instagram.com/${data.username}`,
        [
          data.full_name         && `Full name: ${data.full_name}`,
          data.biography         && `Bio: ${data.biography}`,
          `Followers: ${data.followers} · Following: ${data.following}`,
          `Posts: ${data.posts_count}`,
          data.is_private        && "Account: private",
          data.is_verified       && "Verified account",
          data.external_url      && `External URL: ${data.external_url}`,
          data.business_category && `Business category: ${data.business_category}`,
        ].filter(Boolean).join("\n")
      );
      (data.recent_posts || []).forEach((p, i) =>
        push(
          "Post",
          p.caption?.slice(0, 80) || `Post ${i + 1}`,
          p.url || "",
          [p.caption, p.date && `Date: ${p.date}`, `Likes: ${p.likes}`,
           p.location  && `Location: ${p.location}`,
           p.hashtags?.length && `Hashtags: ${p.hashtags.join(" ")}`,
           p.mentions?.length && `Mentions: ${p.mentions.join(" ")}`]
            .filter(Boolean).join("\n")
        )
      );
      break;
    }

    case "username_enum": {
      const byCategory = data.by_category || {};
      Object.entries(byCategory).forEach(([cat, profiles]) =>
        profiles.forEach((p) => push(cat, p.site, p.url, `${p.site}\n${p.url}`))
      );
      break;
    }

    case "email_osint": {
      if (data.gravatar?.found) {
        const g = data.gravatar;
        push(
          "Gravatar",
          g.display_name || "Gravatar Profile",
          g.profile_url,
          [g.about_me         && `About: ${g.about_me}`,
           g.location         && `Location: ${g.location}`,
           g.accounts?.length && `Linked accounts: ${g.accounts.join(", ")}`,
           g.urls?.length     && `URLs: ${g.urls.join(", ")}`]
            .filter(Boolean).join("\n")
        );
      }
      (data.site_registrations || []).forEach((site) =>
        push("Registration", `Registered on: ${site}`, "", `Email: ${data.email}\nSite: ${site}`)
      );
      break;
    }

    case "linkedin": {
      const sections = [];

      if (data.headline)    sections.push(`HEADLINE\n${data.headline}`);
      if (data.location)    sections.push(`LOCATION\n${data.location}`);
      if (data.connections) sections.push(`CONNECTIONS\n${data.connections}`);
      if (data.about)       sections.push(`ABOUT\n${data.about}`);

      if (data.experience?.length) {
        sections.push(
          `EXPERIENCE\n${data.experience.map((e) =>
            `• ${[e.title, e.company, e.dates].filter(Boolean).join("  |  ")}`
          ).join("\n")}`
        );
      }

      if (data.education?.length) {
        sections.push(
          `EDUCATION\n${data.education.map((e) =>
            `• ${[e.school, e.degree, e.dates].filter(Boolean).join("  |  ")}`
          ).join("\n")}`
        );
      }

      if (data.skills?.length) {
        sections.push(`SKILLS\n${data.skills.join("  ·  ")}`);
      }

      push(
        "Profile",
        `LinkedIn: ${data.name || data.url}`,
        data.url || "",
        sections.join("\n\n")
      );

      if (data.posts?.length) {
        push(
          "Recent Posts",
          `Recent Posts (${data.posts.length})`,
          "",
          data.posts.map((p, i) =>
            [
              `Post ${i + 1}${p.date ? ` · ${p.date}` : ""}${p.likes ? ` · ${p.likes} reactions` : ""}`,
              p.text,
            ].join("\n")
          ).join("\n\n─────────────────────────\n\n")
        );
      }
      break;
    }

    case "claude_research":
    case "gemini_research": {
      (data.findings || []).forEach((f) =>
        push(f.category, f.title, "", f.content || "")
      );
      break;
    }

    default:
      break;
  }

  return items;
}

// ── App ────────────────────────────────────────────────────────────────────
export default function App() {
  // ── State ──────────────────────────────────────────────────────────────
  const [target,          setTarget]          = useState({ name: "", username: "", email: "" });
  const [selectedModules, setSelectedModules] = useState([]);
  const [isGathering,     setIsGathering]     = useState(false);
  const [moduleStatuses,  setModuleStatuses]  = useState({});
  const [flatResults,     setFlatResults]     = useState([]);   // all individual result cards
  const [pinnedItems,     setPinnedItems]     = useState([]);   // items sent to workspace
  const [notes,           setNotes]           = useState("");   // analyst free-text notes
  const [analysisType,    setAnalysisType]    = useState("full");
  const [aiProvider,      setAiProvider]      = useState("claude");
  const [isAnalyzing,     setIsAnalyzing]     = useState(false);
  const [analysis,        setAnalysis]        = useState(null);
  const [error,           setError]           = useState(null);

  // Ref keeps the SSE EventSource so we can close it on reset
  const esRef = useRef(null);

  // ── Handlers ───────────────────────────────────────────────────────────

  /** Toggle a module on/off in the selection list */
  const toggleModule = (id) =>
    setSelectedModules((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );

  /**
   * Start an OSINT gathering session.
   * Opens an SSE connection and appends result cards as modules complete.
   */
  const handleSearch = async (targetData) => {
    if (selectedModules.length === 0)
      return setError("Select at least one module before executing.");
    setError(null);
    setIsGathering(true);
    setFlatResults([]);
    setModuleStatuses({});
    setPinnedItems([]);
    setAnalysis(null);
    setTarget(targetData);

    try {
      const { session_id } = await startGathering(targetData, selectedModules);
      if (esRef.current) esRef.current.close();

      esRef.current = streamResults(
        session_id,
        (update) => {
          if (!update.module) return;
          setModuleStatuses((prev) => ({ ...prev, [update.module]: update.status }));
          if (update.status === "done" && update.data) {
            // Flatten module data and append to the results list
            const newItems = flattenModuleData(update.module, update.data);
            setFlatResults((prev) => [...prev, ...newItems]);
          }
        },
        () => setIsGathering(false)
      );
    } catch (err) {
      setError(err.message || "Gathering failed — check the backend is running.");
      setIsGathering(false);
    }
  };

  /** Pin or unpin a result card.  Same function handles both directions. */
  const handlePinToggle = (item) => {
    setPinnedItems((prev) => {
      const exists = prev.find((p) => p.id === item.id);
      return exists ? prev.filter((p) => p.id !== item.id) : [...prev, item];
    });
  };

  /**
   * Send the pinned cards and analyst notes to the AI analyser.
   * The backend forwards the curated data to Claude for threat assessment.
   */
  const handleAnalyze = async () => {
    if (!pinnedItems.length && !notes.trim())
      return setError("Pin at least one result, or add analyst notes before generating.");
    setError(null);
    setIsAnalyzing(true);
    try {
      // Convert pinned items to the format expected by the backend analyser
      const curatedData = pinnedItems.map((item) => ({
        id:      item.id,
        module:  item.module,
        label:   `[${item.category}] ${item.title}`,
        content: [item.url, item.content].filter(Boolean).join("\n"),
      }));
      // Append manual notes as an extra curated item
      if (notes.trim()) {
        curatedData.push({
          id: "analyst_notes", module: "manual",
          label: "Analyst Notes", content: notes.trim(),
        });
      }
      const data = await analyzeData(target, curatedData, analysisType, aiProvider);
      setAnalysis(data.analysis);
    } catch (err) {
      setError(err.message || "Analysis failed — check the API keys are set.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  /** Reset all state for a new search */
  const handleReset = () => {
    if (esRef.current) esRef.current.close();
    setFlatResults([]); setModuleStatuses({});
    setPinnedItems([]); setAnalysis(null); setError(null);
    setIsGathering(false); setIsAnalyzing(false); setNotes("");
  };

  // ── Derived values ─────────────────────────────────────────────────────
  const hasResults  = flatResults.length > 0;
  const doneCount   = Object.values(moduleStatuses).filter((s) => s === "done").length;
  const statusLabel = isGathering
    ? `GATHERING ${doneCount} / ${selectedModules.length}`
    : isAnalyzing ? "ANALYZING…"
    : hasResults  ? `${flatResults.length} RESULTS · ${pinnedItems.length} PINNED`
    : "READY";

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div className="app-container">
      <Header statusLabel={statusLabel} isLive={isGathering || isAnalyzing} />

      <div className="workspace">

        {/* ── LEFT SIDEBAR ────────────────────────────────────────────── */}
        <aside className="sidebar">
          <div className="sidebar-scroll">

            {/* Target input */}
            <div>
              <label className="section-label">TARGET</label>
              <SearchForm
                onSearch={handleSearch}
                isLoading={isGathering}
                onReset={hasResults || isGathering ? handleReset : null}
              />
            </div>

            {/* Module selection — visible only before the first search */}
            {!isGathering && !hasResults && (
              <div>
                <label className="section-label">MODULES</label>
                <div className="module-list">
                  {ALL_MODULES.map((mod) => (
                    <button
                      key={mod.id}
                      className={`module-toggle ${selectedModules.includes(mod.id) ? "active" : ""}`}
                      onClick={() => toggleModule(mod.id)}
                      title={mod.note}
                    >
                      <span className="module-toggle-dot" />
                      {mod.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Module status — visible during and after gathering */}
            {(isGathering || hasResults) && (
              <div>
                <label className="section-label">MODULE STATUS</label>
                <div className="module-progress">
                  {ALL_MODULES.filter((m) => selectedModules.includes(m.id)).map((mod) => {
                    const status = moduleStatuses[mod.id] || "pending";
                    return (
                      <div key={mod.id} className="module-progress-row">
                        <span className={`dot ${status}`} />
                        <span style={{ flex: 1, fontSize: 10 }}>{mod.label}</span>
                        <span style={{ fontSize: 9, color: "var(--text-dim)" }}>{status}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Status block — pinned to the bottom of the sidebar */}
            <div className="status-block">
              <label className="section-label">STATUS</label>
              <div className={`status-text ${isGathering || isAnalyzing ? "pulse" : ""}`}>
                {statusLabel}
              </div>
            </div>
          </div>
        </aside>

        {/* ── CENTRE PANEL ─────────────────────────────────────────────── */}
        <main className="main-content">
          {error && <div className="error-banner">{error}</div>}

          {/* Welcome screen with step-by-step guide */}
          {!isGathering && !hasResults && (
            <div className="empty-results">
              <div className="empty-results-title">UNITHREAT</div>
              <div className="empty-results-sub">
                Passive OSINT profiling for academic security research
              </div>
              <div className="step-guide">
                {[
                  "Enter target details in the left panel",
                  "Select the OSINT modules to run",
                  "Click EXECUTE — results stream in as modules finish",
                  "Pin relevant cards to the Intel Workspace →",
                  "Add analyst notes, then generate the AI threat assessment",
                ].map((step, i) => (
                  <div key={i} className="step-guide-row">
                    <div className="step-guide-num">{i + 1}</div>
                    <div>{step}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gathering spinner — shown while modules run but no results yet */}
          {isGathering && !hasResults && (
            <div className="empty-results">
              <div className="spinner-ring" />
              <div className="empty-results-title">GATHERING</div>
              <div className="empty-results-sub">
                Running {selectedModules.length} module{selectedModules.length !== 1 ? "s" : ""}.
                Results will appear here as each module completes.
              </div>
            </div>
          )}

          {/* Result cards — rendered as they stream in */}
          {hasResults && (
            <ProfileResults
              flatResults={flatResults}
              pinnedItems={pinnedItems}
              onPinToggle={handlePinToggle}
              isGathering={isGathering}
            />
          )}
        </main>

        {/* ── RIGHT SIDEBAR — Intel Workspace ──────────────────────────── */}
        <TargetDossier
          target={target}
          pinnedItems={pinnedItems}
          onUnpin={handlePinToggle}
          notes={notes}
          onNotesChange={setNotes}
          analysisType={analysisType}
          onAnalysisTypeChange={setAnalysisType}
          aiProvider={aiProvider}
          onAiProviderChange={setAiProvider}
          onGenerate={handleAnalyze}
          isAnalyzing={isAnalyzing}
          analysis={analysis}
        />
      </div>
    </div>
  );
}
