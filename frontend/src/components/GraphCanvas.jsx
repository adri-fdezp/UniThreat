/**
 * GraphCanvas.jsx — The link-analysis canvas, plus the overview minimap
 *
 * Draws entities and links from useGraphView's positions.
 *   - Drag the background to pan, scroll to zoom, drag an entity to move it
 *   - Click an entity to select it; double-click a collection to expand it
 *   - Zoomed far out, entities become coloured dots and labels are hidden
 *
 * Props:
 *   graph       {object}   - { nodes, edges } from buildGraph
 *   graphView   {object}   - Everything returned by useGraphView
 *   selectedId  {string}   - Id of the selected node
 *   onSelect    {Function} - Called with a node id, or null to clear
 *   onExpand    {Function} - Called with a module id to expand its collection
 *   pinnedIds   {Set}      - Ids of pinned result items
 *   filterText  {string}   - Quick-find text; non-matching entities are dimmed
 */

import { useEffect, useMemo, useRef } from "react";
import { EntityIcon, ICON_COLOURS } from "./Icons";
import { matchesFilter, safeUrl } from "../graph/graphModel";

const NODE_RADIUS = 30;
const DOT_ZOOM = 0.38;     // below this, draw dots instead of pictures
const LINK_LABEL_ZOOM = 0.7;

const clip = (text, max = 24) => (text.length > max ? `${text.slice(0, max - 1)}…` : text);

/** Smooth S-curve between two nodes, stopped short so it clears both icons. */
function linkCurve(a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const x1 = a.x + (dx / len) * NODE_RADIUS;
  const y1 = a.y + (dy / len) * NODE_RADIUS;
  const x2 = b.x - (dx / len) * NODE_RADIUS;
  const y2 = b.y - (dy / len) * NODE_RADIUS;
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;

  // Leave and arrive along whichever axis the link mostly travels
  const d = Math.abs(dy) >= Math.abs(dx)
    ? `M${x1} ${y1} C${x1} ${midY} ${x2} ${midY} ${x2} ${y2}`
    : `M${x1} ${y1} C${midX} ${y1} ${midX} ${y2} ${x2} ${y2}`;
  return { d, midX, midY };
}

function hubStatusText(status) {
  if (status === "running") return "Running";
  if (status === "error")   return "Failed";
  if (status === "done")    return "Done";
  return "Waiting";
}

export default function GraphCanvas({ graph, graphView, selectedId, onSelect, onExpand, pinnedIds, filterText }) {
  const { positions, view, setSize, zoomAt, panBy, moveNode, fit } = graphView;
  const svgRef    = useRef(null);
  const gesture   = useRef(null);
  const lastClick = useRef({ id: null, time: 0 });

  // Track the canvas size so fit and the overview stay accurate
  useEffect(() => {
    const svg = svgRef.current;
    const observer = new ResizeObserver(([entry]) => {
      setSize({ w: entry.contentRect.width, h: entry.contentRect.height });
    });
    observer.observe(svg);
    return () => observer.disconnect();
  }, [setSize]);

  // Wheel listener is added by hand because React's is passive and can't stop page scroll
  useEffect(() => {
    const svg = svgRef.current;
    const onWheel = (e) => {
      e.preventDefault();
      const box = svg.getBoundingClientRect();
      zoomAt(Math.exp(-e.deltaY * 0.0012), e.clientX - box.left, e.clientY - box.top);
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [zoomAt]);

  const activate = (node) => {
    onSelect(node.id);
    if (node.kind === "more") onExpand(node.module);
  };

  const onPointerDown = (e, node = null) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    svgRef.current.setPointerCapture(e.pointerId);
    const start = node ? positions[node.id] : null;
    gesture.current = {
      node,
      startX: e.clientX,
      startY: e.clientY,
      lastX:  e.clientX,
      lastY:  e.clientY,
      nodeX:  start?.x,
      nodeY:  start?.y,
      moved:  false,
    };
  };

  const onPointerMove = (e) => {
    const g = gesture.current;
    if (!g) return;
    if (!g.moved && Math.hypot(e.clientX - g.startX, e.clientY - g.startY) < 4) return;
    g.moved = true;
    if (g.node) {
      moveNode(
        g.node.id,
        g.nodeX + (e.clientX - g.startX) / view.k,
        g.nodeY + (e.clientY - g.startY) / view.k,
      );
    } else {
      panBy(e.clientX - g.lastX, e.clientY - g.lastY);
    }
    g.lastX = e.clientX;
    g.lastY = e.clientY;
  };

  const onPointerUp = () => {
    const g = gesture.current;
    gesture.current = null;
    if (!g || g.moved) return;

    if (!g.node) {
      onSelect(null);
      return;
    }
    const now = performance.now();
    const isDouble = lastClick.current.id === g.node.id && now - lastClick.current.time < 320;
    lastClick.current = { id: g.node.id, time: now };
    onSelect(g.node.id);
    if (isDouble && (g.node.kind === "more" || g.node.hidden > 0)) onExpand(g.node.module);
  };

  // Which entities the quick-find leaves undimmed
  const dimmed = useMemo(() => {
    const ids = new Set();
    if (!filterText.trim()) return ids;
    graph.nodes.forEach((n) => {
      if (n.kind === "entity" && !matchesFilter(n.item, filterText)) ids.add(n.id);
    });
    return ids;
  }, [graph, filterText]);

  // Each link takes the colour of the module it belongs to
  const iconById = useMemo(() => {
    const icons = {};
    graph.nodes.forEach((n) => { icons[n.id] = n.icon; });
    return icons;
  }, [graph]);

  const asDots = view.k < DOT_ZOOM;
  const showLinkLabels = view.k >= LINK_LABEL_ZOOM;

  return (
    <svg
      ref={svgRef}
      className="graph-svg"
      role="group"
      aria-label="Entity graph. Use the Entity list view for a table of the same results."
      onPointerDown={(e) => onPointerDown(e)}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={() => { gesture.current = null; }}
      onDoubleClick={(e) => { if (e.target === svgRef.current) fit(); }}
    >
      <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
        {/* Links first, so entities sit on top of them */}
        {graph.edges.map((edge) => {
          const a = positions[edge.from];
          const b = positions[edge.to];
          if (!a || !b) return null;
          const active = selectedId === edge.from || selectedId === edge.to;
          const faded = dimmed.has(edge.to);
          const curve = linkCurve(a, b);
          const colour = ICON_COLOURS[iconById[edge.from === "root" ? edge.to : edge.from]];
          return (
            <g
              key={edge.id}
              className={`graph-link ${active ? "active" : ""} ${faded ? "dimmed" : ""}`}
              style={{ color: colour }}
            >
              <path d={curve.d} />
              {active && showLinkLabels && edge.label && (
                <text x={curve.midX} y={curve.midY - 5} textAnchor="middle">
                  {clip(edge.label, 22)}
                </text>
              )}
            </g>
          );
        })}

        {graph.nodes.map((node) => {
          const p = positions[node.id];
          if (!p) return null;
          const selected = selectedId === node.id;
          const pinned = node.item && pinnedIds.has(node.item.id);
          const size = node.kind === "person" ? 60 : 48;
          const status = node.kind === "hub" ? node.status : null;
          const classes = [
            "graph-node",
            node.kind,
            selected && "selected",
            dimmed.has(node.id) && "dimmed",
            status,
          ].filter(Boolean).join(" ");
          const description = node.kind === "hub"
            ? `${node.label}, ${hubStatusText(status)}, ${node.count} results`
            : node.label;

          return (
            <g
              key={node.id}
              className={classes}
              transform={`translate(${p.x} ${p.y})`}
              tabIndex={0}
              role="button"
              aria-label={description}
              aria-pressed={selected}
              onPointerDown={(e) => onPointerDown(e, node)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  activate(node);
                }
              }}
            >
              <title>{node.label}</title>

              {asDots ? (
                <circle
                  r={node.kind === "entity" ? 26 : 44}
                  fill={ICON_COLOURS[node.icon]}
                  className={`graph-dot ${pinned ? "pinned" : ""}`}
                />
              ) : (
                <>
                  <rect className="node-halo" x={-size / 2 - 7} y={-size / 2 - 7} width={size + 14} height={size + 14} rx="8" />
                  {status === "running" && <circle className="node-running" r={size / 2 + 4} />}
                  <EntityIcon name={node.icon} size={size} x={-size / 2} y={-size / 2} />
                  {/* Image results show their picture, with the icon left behind it in case it fails to load */}
                  {safeUrl(node.item?.thumbnail) && (
                    <image
                      href={safeUrl(node.item.thumbnail)}
                      x={-size / 2}
                      y={-size / 2}
                      width={size}
                      height={size}
                      preserveAspectRatio="xMidYMid slice"
                    />
                  )}

                  {/* Count badge on hubs, and a failed marker when a module errors */}
                  {node.kind === "hub" && status === "error" && (
                    <g className="node-badge error" transform={`translate(${size / 2 - 2} ${-size / 2 + 2})`}>
                      <circle r="9" />
                      <text textAnchor="middle" y="4">!</text>
                    </g>
                  )}
                  {node.kind === "hub" && status !== "error" && node.count > 0 && (
                    <g className="node-badge" transform={`translate(${size / 2 - 2} ${-size / 2 + 2})`}>
                      <rect x={-(String(node.count).length * 4 + 5)} y="-9" width={String(node.count).length * 8 + 10} height="18" rx="9" />
                      <text textAnchor="middle" y="4">{node.count}</text>
                    </g>
                  )}
                  {pinned && (
                    <path
                      className="node-pin"
                      transform={`translate(${size / 2 - 3} ${-size / 2 + 3}) scale(0.72)`}
                      d="m0-11 3.200 6.800 7.400 1-5.400 5.100 1.400 7.400L0 5.600-6.600 9.300l1.400-7.400-5.400-5.100 7.400-1Z"
                    />
                  )}

                  <text className="node-label" textAnchor="middle" y={size / 2 + 17}>
                    {clip(node.label)}
                  </text>
                  {node.kind === "hub" && (
                    <text className="node-sublabel" textAnchor="middle" y={size / 2 + 31}>
                      {hubStatusText(status)}
                    </text>
                  )}
                </>
              )}
            </g>
          );
        })}
      </g>
    </svg>
  );
}

/**
 * Overview — the small whole-graph map in the right dock.
 * The rectangle shows the part of the graph the canvas is currently showing.
 * Click or drag anywhere on it to move the canvas there.
 */
export function Overview({ graph, graphView, canvasClass }) {
  const { positions, view, size, centreOn } = graphView;
  const dragging = useRef(false);

  const bounds = useMemo(() => {
    const points = Object.values(positions);
    if (!points.length) return null;
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const pad = 80;
    const minX = Math.min(...xs) - pad;
    const minY = Math.min(...ys) - pad;
    return { minX, minY, w: Math.max(...xs) + pad - minX, h: Math.max(...ys) + pad - minY };
  }, [positions]);

  const moveTo = (e) => {
    const svg = e.currentTarget;
    const matrix = svg.getScreenCTM();
    if (!matrix) return;
    const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix.inverse());
    centreOn(point.x, point.y);
  };

  if (!bounds) {
    return <div className={`overview-empty ${canvasClass}`}>The whole graph shows here once a run starts.</div>;
  }

  return (
    <svg
      className={`overview-svg ${canvasClass}`}
      viewBox={`${bounds.minX} ${bounds.minY} ${bounds.w} ${bounds.h}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Overview of the whole graph"
      onPointerDown={(e) => {
        dragging.current = true;
        e.currentTarget.setPointerCapture(e.pointerId);
        moveTo(e);
      }}
      onPointerMove={(e) => { if (dragging.current) moveTo(e); }}
      onPointerUp={() => { dragging.current = false; }}
    >
      {graph.edges.map((edge) => {
        const a = positions[edge.from];
        const b = positions[edge.to];
        if (!a || !b) return null;
        return <line key={edge.id} className="overview-link" x1={a.x} y1={a.y} x2={b.x} y2={b.y} vectorEffect="non-scaling-stroke" />;
      })}
      {graph.nodes.map((node) => {
        const p = positions[node.id];
        if (!p) return null;
        const r = Math.max(bounds.w, bounds.h) / (node.kind === "entity" ? 140 : 80);
        return <circle key={node.id} cx={p.x} cy={p.y} r={r} fill={ICON_COLOURS[node.icon]} />;
      })}
      <rect
        className="overview-viewport"
        x={-view.x / view.k}
        y={-view.y / view.k}
        width={size.w / view.k}
        height={size.h / view.k}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
