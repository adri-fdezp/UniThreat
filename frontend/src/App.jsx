/**
 * App.jsx — Root component for UniThreat
 *
 * Manages the link-analysis workbench and all top-level application state:
 *   - RIBBON        : run, selection, layout, zoom and panel controls
 *   - LEFT PANEL    : target form, source selection, live source status
 *   - GRAPH         : OSINT results as linked entities (streamed in real time),
 *                     with an entity list view of the same results
 *   - ACTIVITY LOG  : a running log of what each module returned
 *   - RIGHT DOCK    : overview map, detail view, Intel workspace, spam checker
 *
 * Workflow:
 *   1. User fills in the target and selects sources → clicks Run analysis
 *   2. Backend runs modules in parallel and streams progress via SSE
 *   3. Results are flattened into individual entities as each module completes
 *   4. User pins relevant entities to the Intel workspace
 *   5. User adds analyst notes, selects analysis type, clicks Generate
 *   6. Claude analyses the pinned data and returns a structured threat report
 */

import { useState, useRef, useMemo, useEffect } from "react";
import { startGathering, streamResults, analyzeData } from "./api/profiler";
import Header        from "./components/Header";
import SearchForm    from "./components/SearchForm";
import ProfileResults from "./components/ProfileResults";
import TargetDossier from "./components/TargetDossier";
import GraphCanvas, { Overview } from "./components/GraphCanvas";
import { EntityIcon, UiIcon } from "./components/Icons";
import { buildGraph, entityNode, matchesFilter } from "./graph/graphModel";
import { useGraphView } from "./graph/useGraphView";
import "./styles/App.css";

// ── Module registry ────────────────────────────────────────────────────────
// Add new OSINT modules here.  The id must match the backend module key.
const ALL_MODULES = [
  { id: "google",          label: "Google",          note: "Selenium — visible browser, manual CAPTCHA if needed" },
  { id: "duckduckgo",      label: "DuckDuckGo",      note: "Fast API-based web dorks (15+ query templates)" },
  { id: "instagram",       label: "Instagram",       note: "Profile and recent posts (requires username and a logged-in session)" },
  { id: "linkedin",        label: "LinkedIn",        note: "Full profile scrape — requires LinkedIn URL and credentials in .env" },
  { id: "username_enum",   label: "Username",        note: "500+ site enumeration via WhatsMyName dataset" },
  { id: "email_osint",     label: "Email OSINT",     note: "Gravatar lookup + Holehe site registrations" },
  { id: "claude_research", label: "Claude research", note: "AI-driven OSINT profile — identity, presence, search queries" },
];

const EMPTY_TARGET = { name: "", username: "", email: "" };

const STATUS_TEXT = { pending: "Waiting", running: "Running", done: "Finished", error: "Failed" };

const GUIDE_STEPS = [
  "Enter the person's name, plus any username, email or LinkedIn URL you know.",
  "Tick the sources to search.",
  "Select Run analysis. Entities appear on the graph as each source finishes.",
  "Select an entity and pin the useful ones to the Intel workspace.",
  "Add your notes, then generate the attack vector analysis.",
];

const logTime = () => new Date().toLocaleTimeString([], { hour12: false });

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
          `EXPERIENCE\n${data.experience.map((e) => {
            const period = e.start
              ? `${e.start} → ${e.end || "Present"}${e.duration ? ` (${e.duration})` : ""}`
              : e.dates || "";
            return [
              `• ${[e.title, e.company].filter(Boolean).join(" @ ")}`,
              period      && `  ${period}`,
              e.location  && `  ${e.location}`,
              e.description && `  ${e.description}`,
            ].filter(Boolean).join("\n");
          }).join("\n\n")}`
        );
      }

      if (data.education?.length) {
        sections.push(
          `EDUCATION\n${data.education.map((e) => {
            const period = e.start
              ? `${e.start} → ${e.end || ""}${e.duration ? ` (${e.duration})` : ""}`.trimEnd()
              : e.dates || "";
            return `• ${[e.school, e.degree].filter(Boolean).join(" · ")}${period ? `  |  ${period}` : ""}`;
          }).join("\n")}`
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

      // Career timeline card — one line per event, structured for the AI
      if (data.timeline?.length) {
        const timelineText = data.timeline.map((ev) => {
          if (ev.type === "experience") {
            return [
              `[JOB]  ${ev.title}${ev.company ? ` @ ${ev.company}` : ""}`,
              ev.period   && `       ${ev.period}`,
              ev.location && `       ${ev.location}`,
              ev.description && `       ${ev.description}`,
            ].filter(Boolean).join("\n");
          }
          if (ev.type === "education") {
            return [
              `[EDU]  ${ev.school}${ev.degree ? ` · ${ev.degree}` : ""}`,
              ev.period && `       ${ev.period}`,
            ].filter(Boolean).join("\n");
          }
          if (ev.type === "post") {
            const dateLabel = ev.date ? ` [${ev.date}]` : "";
            return `[POST]${dateLabel} ${ev.text?.slice(0, 120)}${ev.text?.length > 120 ? "…" : ""}`;
          }
          return "";
        }).filter(Boolean).join("\n\n");

        push(
          "Timeline",
          `Career Timeline — ${data.name || "target"} (${data.timeline.length} events)`,
          data.url || "",
          timelineText,
        );
      }

      if (data.posts?.length) {
        push(
          "Recent Posts",
          `Recent Posts (${data.posts.length})`,
          "",
          data.posts.map((p, i) => {
            const datePart = p.date_iso
              ? `${p.date_iso}${p.date ? ` · ${p.date}` : ""}`
              : p.date || "";
            return [
              `Post ${i + 1}${datePart ? ` · ${datePart}` : ""}${p.likes ? ` · ${p.likes} reactions` : ""}`,
              p.text,
            ].join("\n");
          }).join("\n\n─────────────────────────\n\n")
        );
      }
      break;
    }

    case "claude_research": {
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

// ── Output log ─────────────────────────────────────────────────────────────
/** Running log of what each module did, newest line at the bottom. */
function ActivityLog({ entries }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries]);

  return (
    <section className="output-panel" aria-label="Activity log">
      <h2 className="panel-title">Activity log</h2>
      <div className="output-scroll" ref={scrollRef} role="log">
        {entries.length === 0 && <div className="output-empty">Nothing has run yet.</div>}
        {entries.map((entry) => (
          <div key={entry.id} className={`output-line ${entry.level}`}>
            <span className="output-time">{entry.time}</span>
            <span className="output-source">{entry.source}</span>
            <span className="output-text">{entry.text}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── App ────────────────────────────────────────────────────────────────────
export default function App() {
  // ── State ──────────────────────────────────────────────────────────────
  const [target,          setTarget]          = useState(EMPTY_TARGET);
  const [selectedModules, setSelectedModules] = useState([]);
  const [isGathering,     setIsGathering]     = useState(false);
  const [hasRun,          setHasRun]          = useState(false);  // a run has started on this graph
  const [moduleStatuses,  setModuleStatuses]  = useState({});
  const [moduleErrors,    setModuleErrors]    = useState({});
  const [flatResults,     setFlatResults]     = useState([]);   // all individual results
  const [pinnedItems,     setPinnedItems]     = useState([]);   // items sent to workspace
  const [notes,           setNotes]           = useState("");   // analyst free-text notes
  const [analysisType,    setAnalysisType]    = useState("full");
  const [isAnalyzing,     setIsAnalyzing]     = useState(false);
  const [analysis,        setAnalysis]        = useState(null);
  const [error,           setError]           = useState(null);

  // View state: none of this changes what the modules do
  const [selectedId,  setSelectedId]  = useState(null);
  const [expanded,    setExpanded]    = useState([]);       // modules showing every result
  const [filterText,  setFilterText]  = useState("");
  const [mainView,    setMainView]    = useState("graph");  // "graph" | "list"
  const [dockTab,     setDockTab]     = useState("detail");
  const [canvasLight, setCanvasLight] = useState(false);
  const [panels,      setPanels]      = useState({ palette: true, dock: true, output: true });
  const [runLog,      setRunLog]      = useState([]);

  // Ref keeps the SSE EventSource so we can close it on reset
  const esRef  = useRef(null);
  const logSeq = useRef(0);

  const activeModules = useMemo(
    () => ALL_MODULES.filter((m) => selectedModules.includes(m.id)),
    [selectedModules],
  );

  const graph = useMemo(
    () => buildGraph({
      target:   hasRun ? target : EMPTY_TARGET,
      items:    flatResults,
      modules:  activeModules,
      statuses: moduleStatuses,
      errors:   moduleErrors,
      expanded,
    }),
    [hasRun, target, flatResults, activeModules, moduleStatuses, moduleErrors, expanded],
  );
  const graphView = useGraphView(graph);

  // ── Handlers ───────────────────────────────────────────────────────────

  const addLog = (source, text, level = "info") =>
    setRunLog((prev) => [...prev, { id: logSeq.current++, time: logTime(), source, text, level }]);

  const moduleLabel = (id) => ALL_MODULES.find((m) => m.id === id)?.label || id;

  /** Toggle a module on/off in the selection list */
  const toggleModule = (id) =>
    setSelectedModules((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );

  /**
   * Start an OSINT gathering session.
   * Opens an SSE connection and appends results as modules complete.
   */
  const handleSearch = async (targetData) => {
    if (selectedModules.length === 0)
      return setError("Tick at least one source before running.");
    setError(null);
    setIsGathering(true);
    setHasRun(true);
    setFlatResults([]);
    setModuleStatuses({});
    setModuleErrors({});
    setPinnedItems([]);
    setAnalysis(null);
    setSelectedId(null);
    setExpanded([]);
    setTarget(targetData);
    setRunLog([]);
    addLog("Run", `Searching ${selectedModules.length} source${selectedModules.length !== 1 ? "s" : ""} for ${targetData.name}`);

    try {
      const { session_id } = await startGathering(targetData, selectedModules);
      if (esRef.current) esRef.current.close();

      esRef.current = streamResults(
        session_id,
        (update) => {
          if (!update.module) return;
          const label = moduleLabel(update.module);
          // A module can finish normally yet report a failure in its data
          const failure = update.data?.error;
          setModuleStatuses((prev) => ({ ...prev, [update.module]: failure ? "error" : update.status }));

          if (failure) {
            setModuleErrors((prev) => ({ ...prev, [update.module]: failure }));
            addLog(label, failure, "error");
          } else if (update.status === "running") {
            addLog(label, "Running");
          } else if (update.status === "done" && update.data) {
            // Flatten module data and append to the results list
            const newItems = flattenModuleData(update.module, update.data);
            setFlatResults((prev) => [...prev, ...newItems]);
            addLog(label, `Returned ${newItems.length} entit${newItems.length === 1 ? "y" : "ies"}`, "success");
          }
        },
        () => {
          setIsGathering(false);
          addLog("Run", "All sources finished");
        }
      );
    } catch (err) {
      setError(err.message || "Gathering failed — check the backend is running.");
      addLog("Run", err.message || "Gathering failed", "error");
      setIsGathering(false);
    }
  };

  /** Pin or unpin a result.  Same function handles both directions. */
  const handlePinToggle = (item) => {
    setPinnedItems((prev) => {
      const exists = prev.find((p) => p.id === item.id);
      return exists ? prev.filter((p) => p.id !== item.id) : [...prev, item];
    });
  };

  /**
   * Send the pinned items and analyst notes to the AI analyser.
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
      const data = await analyzeData(target, curatedData, analysisType);
      setAnalysis(data.analysis);
      addLog("Attack vectors", "Attack vector analysis generated", "success");
    } catch (err) {
      setError(err.message || "Analysis failed — check the API keys are set.");
      addLog("Attack vectors", err.message || "Analysis failed", "error");
    } finally {
      setIsAnalyzing(false);
    }
  };

  /** Reset all state for a new search */
  const handleReset = () => {
    if (esRef.current) esRef.current.close();
    setFlatResults([]); setModuleStatuses({}); setModuleErrors({});
    setPinnedItems([]); setAnalysis(null); setError(null);
    setIsGathering(false); setIsAnalyzing(false); setNotes("");
    setHasRun(false); setTarget(EMPTY_TARGET); setRunLog([]);
    setSelectedId(null); setExpanded([]); setFilterText("");
    graphView.resetView();
  };

  /** Select a node and bring its properties into view. */
  const handleSelect = (id) => {
    setSelectedId(id);
    if (id) setDockTab("detail");
  };

  const handleExpand = (moduleId) =>
    setExpanded((prev) => (prev.includes(moduleId) ? prev : [...prev, moduleId]));

  const handleOpenTab = (tab) => {
    setDockTab(tab);
    setPanels((prev) => ({ ...prev, dock: true }));
  };

  // ── Derived values ─────────────────────────────────────────────────────
  const hasResults    = flatResults.length > 0;
  const resultCounts  = flatResults.reduce((acc, item) => {
    acc[item.module] = (acc[item.module] || 0) + 1;
    return acc;
  }, {});

  // A result can be selected from the list while hidden in a collection on the graph
  const selectedNode = useMemo(() => {
    if (!selectedId) return null;
    const onGraph = graph.nodes.find((n) => n.id === selectedId);
    if (onGraph) return onGraph;
    const item = flatResults.find((i) => `e_${i.id}` === selectedId);
    return item ? entityNode(item) : null;
  }, [selectedId, graph, flatResults]);

  const pinnedIds = useMemo(() => new Set(pinnedItems.map((p) => p.id)), [pinnedItems]);

  const filteredCount = useMemo(
    () => flatResults.filter((r) => matchesFilter(r, filterText)).length,
    [flatResults, filterText],
  );

  const canvasClass = canvasLight ? "canvas-light" : "";

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div className="app-container">
      <Header
        canRun={!isGathering && !hasRun}
        onNewGraph={hasRun ? handleReset : null}
        selection={selectedNode}
        isPinned={!!selectedNode?.item && pinnedIds.has(selectedNode.item.id)}
        onPinToggle={handlePinToggle}
        onExpand={handleExpand}
        onOpenTab={handleOpenTab}
        graphView={graphView}
        canvasLight={canvasLight}
        onCanvasLight={setCanvasLight}
        panels={panels}
        onPanelToggle={(name) => setPanels((prev) => ({ ...prev, [name]: !prev[name] }))}
      />

      <div className="workspace">

        {/* ── LEFT PANEL ──────────────────────────────────────────────── */}
        <aside className={`sidebar ${panels.palette ? "" : "is-hidden"}`}>
          <div className="sidebar-scroll">

            {/* Target input */}
            <section>
              <h2 className="panel-title">Target</h2>
              <SearchForm
                onSearch={handleSearch}
                isLoading={isGathering}
                onReset={hasRun ? handleReset : null}
              />
            </section>

            {/* Module selection — visible only before the first search */}
            {!hasRun && (
              <section>
                <h2 className="panel-title">Sources ({selectedModules.length} of {ALL_MODULES.length})</h2>
                <div className="module-list">
                  {ALL_MODULES.map((mod) => (
                    <label
                      key={mod.id}
                      className={`module-toggle ${selectedModules.includes(mod.id) ? "active" : ""}`}
                      title={mod.note}
                    >
                      <input
                        type="checkbox"
                        checked={selectedModules.includes(mod.id)}
                        onChange={() => toggleModule(mod.id)}
                      />
                      <EntityIcon name={`mod_${mod.id}`} size={20} />
                      <span>{mod.label}</span>
                    </label>
                  ))}
                </div>
              </section>
            )}

            {/* Module status — visible during and after gathering */}
            {hasRun && (
              <section>
                <h2 className="panel-title">Sources</h2>
                <div className="module-progress">
                  {activeModules.map((mod) => {
                    const status = moduleStatuses[mod.id] || "pending";
                    const count  = resultCounts[mod.id] || 0;
                    return (
                      <button
                        type="button"
                        key={mod.id}
                        className={`module-progress-row ${selectedId === `hub_${mod.id}` ? "selected" : ""}`}
                        onClick={() => handleSelect(`hub_${mod.id}`)}
                      >
                        <EntityIcon name={`mod_${mod.id}`} size={20} />
                        <span className="module-progress-name">{mod.label}</span>
                        {count > 0 && <span className="module-progress-count">{count}</span>}
                        <span className={`module-progress-status ${status}`}>{STATUS_TEXT[status]}</span>
                      </button>
                    );
                  })}
                </div>
              </section>
            )}
          </div>
        </aside>

        {/* ── GRAPH ────────────────────────────────────────────────────── */}
        <main className="main-content">
          <div className="graph-tabs">
            <div className="graph-tab">
              <UiIcon name="graphView" size={14} />
              <span>{target.name || "New graph"}</span>
            </div>
          </div>

          <div className="graph-toolbar">
            <div className="view-switch" role="group" aria-label="Result view">
              <button
                type="button"
                className={mainView === "graph" ? "active" : ""}
                aria-pressed={mainView === "graph"}
                onClick={() => setMainView("graph")}
              >
                <UiIcon name="graphView" size={14} /> Main view
              </button>
              <button
                type="button"
                className={mainView === "list" ? "active" : ""}
                aria-pressed={mainView === "list"}
                onClick={() => setMainView("list")}
              >
                <UiIcon name="listView" size={14} /> Entity list
              </button>
            </div>
            <input
              className="filter-input"
              type="search"
              placeholder="Filter results by keyword…"
              aria-label="Filter results by keyword"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
            />
            {hasResults && <span className="result-count">{filteredCount} of {flatResults.length} results</span>}
          </div>

          {error && <div className="error-banner">{error}</div>}

          <div className={`graph-stage ${canvasClass}`}>
            <div className={`graph-layer ${hasRun && mainView === "list" ? "is-behind" : ""}`}>
              <GraphCanvas
                graph={graph}
                graphView={graphView}
                selectedId={selectedId}
                onSelect={handleSelect}
                onExpand={handleExpand}
                pinnedIds={pinnedIds}
                filterText={filterText}
              />
            </div>

            {/* Welcome guide, drawn on the empty canvas */}
            {!hasRun && (
              <div className="graph-guide">
                <h1>Start an investigation</h1>
                <ol>
                  {GUIDE_STEPS.map((step) => <li key={step}>{step}</li>)}
                </ol>
              </div>
            )}

            {hasRun && mainView === "list" && (
              <div className="list-layer">
                <ProfileResults
                  flatResults={flatResults}
                  pinnedItems={pinnedItems}
                  onPinToggle={handlePinToggle}
                  isGathering={isGathering}
                  filterText={filterText}
                  selectedId={selectedId}
                  onSelect={handleSelect}
                />
              </div>
            )}
          </div>

          {panels.output && <ActivityLog entries={runLog} />}
        </main>

        {/* ── RIGHT DOCK ───────────────────────────────────────────────── */}
        <TargetDossier
          target={target}
          pinnedItems={pinnedItems}
          onUnpin={handlePinToggle}
          notes={notes}
          onNotesChange={setNotes}
          analysisType={analysisType}
          onAnalysisTypeChange={setAnalysisType}
          onGenerate={handleAnalyze}
          isAnalyzing={isAnalyzing}
          analysis={analysis}
          activeTab={dockTab}
          onTabChange={setDockTab}
          selectedNode={selectedNode}
          onPinToggle={handlePinToggle}
          onExpand={handleExpand}
          hidden={!panels.dock}
          overview={<Overview graph={graph} graphView={graphView} canvasClass={canvasClass} />}
        />
      </div>
    </div>
  );
}
