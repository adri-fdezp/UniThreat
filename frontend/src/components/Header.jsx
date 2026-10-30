/**
 * Header.jsx — Title bar and ribbon
 *
 * Investigate holds the actions for a run and the selected entity.
 * View holds the graph layout, zoom, canvas colour and panel toggles.
 *
 * Props:
 *   canRun     {boolean}  - Enables Run analysis
 *   onNewGraph {Function} - Clears the graph; null when there is nothing to clear
 *   selection  {object}   - Selected node, or null
 *   isPinned   {boolean}  - True when the selected entity is pinned
 *   onPinToggle, onExpand, onOpenTab - Selection and panel actions
 *   graphView  {object}   - Everything returned by useGraphView
 *   canvasLight, onCanvasLight - Graph canvas colour
 *   panels, onPanelToggle      - { palette, dock, output } visibility
 */

import { useState } from "react";
import { UiIcon } from "./Icons";
import { safeUrl } from "../graph/graphModel";

function RibbonButton({ icon, label, active = false, small = false, filled = false, ...rest }) {
  return (
    <button
      type="button"
      className={`ribbon-btn ${small ? "small" : ""} ${active ? "active" : ""}`}
      aria-pressed={active || undefined}
      {...rest}
    >
      <UiIcon name={icon} size={small ? 16 : 22} filled={filled} />
      <span>{label}</span>
    </button>
  );
}

function RibbonGroup({ title, children }) {
  return (
    <div className="ribbon-group" role="group" aria-label={title}>
      <div className="ribbon-group-items">{children}</div>
      <div className="ribbon-group-title">{title}</div>
    </div>
  );
}

export default function Header({
  canRun,
  onNewGraph,
  selection,
  isPinned,
  onPinToggle,
  onExpand,
  onOpenTab,
  graphView,
  canvasLight,
  onCanvasLight,
  panels,
  onPanelToggle,
}) {
  const [tab,       setTab]       = useState("investigate");
  const [collapsed, setCollapsed] = useState(false);

  const item = selection?.item;
  const itemLink = safeUrl(item?.url);

  return (
    <header className="app-header">
      <div className="title-bar">
        <svg className="app-mark" width="22" height="22" viewBox="0 0 20 20" aria-hidden="true">
          <g fill="#5db2ee">
            <circle cx="10" cy="4" r="2.600" />
            <circle cx="3.500" cy="15" r="2.600" />
            <circle cx="16.500" cy="15" r="2.600" />
          </g>
          <path d="M10 4 3.500 15h13Z" fill="none" stroke="#5db2ee" strokeWidth="1.300" />
        </svg>
        <strong>UniThreat</strong>
        <span className="title-meta">
          <span>A Never0Risk app</span>
          <span>Version 0.2</span>
        </span>
      </div>

      <div className="ribbon-tabs" role="tablist" aria-label="Ribbon">
        {[
          { id: "investigate", label: "Investigate" },
          { id: "view",        label: "View" },
        ].map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`ribbon-tab ${tab === t.id ? "active" : ""}`}
            onClick={() => { setTab(t.id); setCollapsed(false); }}
          >
            {t.label}
          </button>
        ))}
        <button
          type="button"
          className="ribbon-collapse"
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? "Show ribbon" : "Hide ribbon"}
          title={collapsed ? "Show ribbon" : "Hide ribbon"}
        >
          <UiIcon name={collapsed ? "chevronDown" : "chevronUp"} size={14} />
        </button>
      </div>

      {!collapsed && tab === "investigate" && (
        <div className="ribbon-body">
          <RibbonGroup title="Run">
            <RibbonButton icon="run" label="Run analysis" type="submit" form="target-form" disabled={!canRun} />
            <RibbonButton icon="newGraph" label="New graph" onClick={onNewGraph} disabled={!onNewGraph} />
          </RibbonGroup>

          <RibbonGroup title="Selected entity">
            <RibbonButton
              icon="star"
              filled={isPinned}
              label={isPinned ? "Unpin" : "Pin to workspace"}
              onClick={() => onPinToggle(item)}
              disabled={!item}
            />
            <RibbonButton
              icon="link"
              label="Open link"
              onClick={() => window.open(itemLink, "_blank", "noreferrer")}
              disabled={!itemLink}
            />
            <RibbonButton
              icon="expand"
              label="Show all"
              onClick={() => onExpand(selection.module)}
              disabled={!(selection?.hidden > 0)}
            />
          </RibbonGroup>

          <RibbonGroup title="Tools">
            <RibbonButton icon="workspace" label="Intel workspace" onClick={() => onOpenTab("intel")} />
            <RibbonButton icon="mail" label="Spam checker" onClick={() => onOpenTab("spam")} />
          </RibbonGroup>
        </div>
      )}

      {!collapsed && tab === "view" && (
        <div className="ribbon-body">
          <RibbonGroup title="Layout">
            <RibbonButton icon="block" label="Block" active={graphView.layout === "block"} onClick={() => graphView.setLayout("block")} />
            <RibbonButton icon="hierarchical" label="Hierarchical" active={graphView.layout === "hierarchical"} onClick={() => graphView.setLayout("hierarchical")} />
            <RibbonButton icon="circular" label="Circular" active={graphView.layout === "circular"} onClick={() => graphView.setLayout("circular")} />
          </RibbonGroup>

          <RibbonGroup title="Zoom">
            <RibbonButton icon="zoomIn" label="Zoom in" onClick={() => graphView.zoomBy(1.25)} />
            <RibbonButton icon="zoomOut" label="Zoom out" onClick={() => graphView.zoomBy(0.8)} />
            <RibbonButton icon="fit" label="Fit graph" onClick={graphView.fit} />
          </RibbonGroup>

          <RibbonGroup title="Graph colour">
            <RibbonButton icon="canvas" label="Dark" active={!canvasLight} onClick={() => onCanvasLight(false)} />
            <RibbonButton icon="canvas" label="Light" active={canvasLight} onClick={() => onCanvasLight(true)} />
          </RibbonGroup>

          <RibbonGroup title="Panels">
            <RibbonButton icon="palette" label="Target" active={panels.palette} onClick={() => onPanelToggle("palette")} />
            <RibbonButton icon="dock" label="Details" active={panels.dock} onClick={() => onPanelToggle("dock")} />
            <RibbonButton icon="output" label="Activity log" active={panels.output} onClick={() => onPanelToggle("output")} />
          </RibbonGroup>
        </div>
      )}
    </header>
  );
}
