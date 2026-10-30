/**
 * DetailView.jsx — Properties of the entity selected on the graph
 *
 * Props:
 *   node        {object}   - Selected node, or null
 *   isPinned    {boolean}  - True when the selected entity is pinned
 *   onPinToggle {Function} - Called with the item to pin or unpin it
 *   onExpand    {Function} - Called with a module id to expand its collection
 */

import { EntityIcon, UiIcon } from "./Icons";
import { safeUrl } from "../graph/graphModel";

const STATUS_TEXT = { pending: "Waiting", running: "Running", done: "Finished", error: "Failed" };

function PropertyRow({ name, children }) {
  return (
    <div className="property-row">
      <dt>{name}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export default function DetailView({ node, isPinned, onPinToggle, onExpand }) {
  if (!node) {
    return <div className="panel-empty">Select an entity on the graph to see its properties.</div>;
  }

  const { item, target } = node;

  return (
    <div className="detail-view">
      <div className="detail-head">
        <EntityIcon name={node.icon} size={40} />
        <div className="detail-title">{node.label}</div>
      </div>

      <dl className="property-grid">
        {node.kind === "person" && (
          <>
            <PropertyRow name="Name">{target.name}</PropertyRow>
            {target.username     && <PropertyRow name="Username">{target.username}</PropertyRow>}
            {target.email        && <PropertyRow name="Email">{target.email}</PropertyRow>}
            {target.linkedin_url && <PropertyRow name="LinkedIn URL">{target.linkedin_url}</PropertyRow>}
          </>
        )}

        {node.kind === "identifier" && <PropertyRow name="Value">{node.label}</PropertyRow>}

        {node.kind === "hub" && (
          <>
            <PropertyRow name="Status">{STATUS_TEXT[node.status]}</PropertyRow>
            <PropertyRow name="Results">{node.count}</PropertyRow>
            <PropertyRow name="What it does">{node.note}</PropertyRow>
          </>
        )}

        {node.kind === "more" && <PropertyRow name="Hidden results">{node.hidden}</PropertyRow>}

        {item && (
          <>
            <PropertyRow name="Category">{item.category}</PropertyRow>
            {item.url && (
              <PropertyRow name="Link">
                {safeUrl(item.url)
                  ? <a href={safeUrl(item.url)} target="_blank" rel="noreferrer">{item.url}</a>
                  : item.url}
              </PropertyRow>
            )}
          </>
        )}
      </dl>

      {node.error && <div className="error-banner detail-error">{node.error}</div>}

      {node.hidden > 0 && (
        <button type="button" className="secondary-btn" onClick={() => onExpand(node.module)}>
          Show all {node.hidden} hidden results
        </button>
      )}

      {item && (
        <button
          type="button"
          className={`secondary-btn with-icon ${isPinned ? "is-on" : ""}`}
          onClick={() => onPinToggle(item)}
        >
          <UiIcon name="star" size={15} filled={isPinned} />
          {isPinned ? "Remove from workspace" : "Pin to workspace"}
        </button>
      )}

      {item?.content && <div className="detail-content">{item.content}</div>}
    </div>
  );
}
