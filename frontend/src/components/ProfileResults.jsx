/**
 * ProfileResults.jsx — Entity list view
 *
 * The same results as the graph, as a table: one row per hit.
 * Selecting a row shows it in the detail view, and the star pins it to the
 * Intel workspace.
 *
 * Props:
 *   flatResults  {Array}    - All flattened result items from all modules
 *   pinnedItems  {Array}    - Currently pinned items (used to mark rows)
 *   onPinToggle  {Function} - Called with an item to pin or unpin it
 *   isGathering  {boolean}  - True while modules are still running
 *   filterText   {string}   - Quick-find text from the graph toolbar
 *   selectedId   {string}   - Id of the selected node
 *   onSelect     {Function} - Called with the node id of a clicked row
 */

import { useMemo } from "react";
import { EntityIcon, UiIcon } from "./Icons";
import { entityNode, matchesFilter, safeUrl } from "../graph/graphModel";

// Human-readable labels for the source column
const MODULE_LABELS = {
  google:          "Google",
  duckduckgo:      "DuckDuckGo",
  instagram:       "Instagram",
  linkedin:        "LinkedIn",
  username_enum:   "Username",
  email_osint:     "Email OSINT",
  claude_research: "Claude research",
};

export default function ProfileResults({ flatResults, pinnedItems, onPinToggle, isGathering, filterText, selectedId, onSelect }) {
  const filtered = useMemo(
    () => flatResults.filter((r) => matchesFilter(r, filterText)),
    [flatResults, filterText],
  );

  if (filtered.length === 0) {
    return (
      <div className="list-empty">
        {flatResults.length === 0
          ? (isGathering ? "Waiting for results…" : "This run returned no results. Check the Activity log for the reason.")
          : "No results match the current filter."}
      </div>
    );
  }

  return (
    <div className="entity-table-wrap">
      <table className="entity-table">
        <thead>
          <tr>
            <th scope="col" className="col-pin"><span className="sr-only">Pinned</span></th>
            <th scope="col">Entity</th>
            <th scope="col">Source</th>
            <th scope="col">Category</th>
            <th scope="col">Link</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((item) => {
            const node = entityNode(item);
            const isPinned = pinnedItems.some((p) => p.id === item.id);
            return (
              <tr
                key={item.id}
                className={selectedId === node.id ? "selected" : ""}
                onClick={() => onSelect(node.id)}
              >
                <td className="col-pin">
                  <button
                    type="button"
                    className={`pin-btn ${isPinned ? "pinned-btn" : ""}`}
                    onClick={(e) => { e.stopPropagation(); onPinToggle(item); }}
                    aria-label={isPinned ? `Unpin ${item.title}` : `Pin ${item.title}`}
                    title={isPinned ? "Remove from workspace" : "Add to workspace"}
                  >
                    <UiIcon name="star" size={15} filled={isPinned} />
                  </button>
                </td>
                <td className="col-entity">
                  <EntityIcon name={node.icon} size={20} />
                  <button
                    type="button"
                    className="entity-name-btn"
                    onClick={(e) => { e.stopPropagation(); onSelect(node.id); }}
                  >
                    {item.title}
                  </button>
                </td>
                <td>{MODULE_LABELS[item.module] || item.module}</td>
                <td>{item.category}</td>
                <td className="col-link">
                  {safeUrl(item.url) ? (
                    <a href={safeUrl(item.url)} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
                      {item.url}
                    </a>
                  ) : item.url}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
