/**
 * useGraphView.js — Pan, zoom, layout and node positions for the graph
 *
 * Lives in a hook because three separate panels share it: the ribbon sets the
 * layout and zoom, the canvas draws it, and the overview shows where you are.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LAYOUTS, fitView } from "./graphModel";

const MIN_ZOOM = 0.08;
const MAX_ZOOM = 2.5;
const ANIMATION_MS = 320;

const clampZoom = (k) => Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, k));

export function useGraphView(graph) {
  const [layout,  setLayoutName] = useState("circular");
  const [manual,  setManual]     = useState({});   // positions set by dragging a node
  const [view,    setView]       = useState({ x: 0, y: 0, k: 1 });
  const [size,    setSize]       = useState({ w: 0, h: 0 });
  const [display, setDisplay]    = useState({});   // positions drawn this frame

  const displayRef = useRef(display);
  const frameRef   = useRef(0);
  const skipAnim   = useRef(false);
  const autoFit    = useRef(true);                 // stops once the user pans or zooms
  displayRef.current = display;

  const parents = useMemo(() => {
    const map = {};
    graph.nodes.forEach((n) => { map[n.id] = n.parent; });
    return map;
  }, [graph]);

  const layoutPositions = useMemo(() => LAYOUTS[layout](graph), [graph, layout]);

  // Dragged positions win over the layout, but only for nodes still on the graph
  const target = useMemo(() => {
    const merged = { ...layoutPositions };
    Object.entries(manual).forEach(([id, p]) => {
      if (merged[id]) merged[id] = p;
    });
    return merged;
  }, [layoutPositions, manual]);

  // Glide nodes to their new positions; new entities grow out of their parent
  useEffect(() => {
    cancelAnimationFrame(frameRef.current);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (skipAnim.current || reduced) {
      skipAnim.current = false;
      setDisplay(target);
      return undefined;
    }

    const from  = displayRef.current;
    const start = performance.now();
    const step  = (now) => {
      const t = Math.min(1, (now - start) / ANIMATION_MS);
      const e = 1 - (1 - t) ** 3;
      const next = {};
      Object.entries(target).forEach(([id, to]) => {
        const origin = from[id] || from[parents[id]] || to;
        next[id] = { x: origin.x + (to.x - origin.x) * e, y: origin.y + (to.y - origin.y) * e };
      });
      setDisplay(next);
      if (t < 1) frameRef.current = requestAnimationFrame(step);
    };
    frameRef.current = requestAnimationFrame(step);

    // Browsers pause animation frames in background windows; results must still land
    const fallback = setTimeout(() => {
      cancelAnimationFrame(frameRef.current);
      setDisplay(target);
    }, ANIMATION_MS + 80);

    return () => {
      cancelAnimationFrame(frameRef.current);
      clearTimeout(fallback);
    };
  }, [target, parents]);

  // Keep the whole graph in view while results stream in, until the user takes over
  useEffect(() => {
    if (autoFit.current && size.w) setView(fitView(target, size));
  }, [target, size]);

  const setLayout = useCallback((name) => {
    setManual({});
    autoFit.current = true;
    setLayoutName(name);
  }, []);

  const fit = useCallback(() => {
    autoFit.current = true;
    setView(fitView(target, size));
  }, [target, size]);

  /** Zoom by a factor, keeping the given canvas point still. */
  const zoomAt = useCallback((factor, cx, cy) => {
    autoFit.current = false;
    setView((v) => {
      const k = clampZoom(v.k * factor);
      const ratio = k / v.k;
      return { k, x: cx - (cx - v.x) * ratio, y: cy - (cy - v.y) * ratio };
    });
  }, []);

  const zoomBy = useCallback(
    (factor) => zoomAt(factor, size.w / 2, size.h / 2),
    [zoomAt, size],
  );

  const panBy = useCallback((dx, dy) => {
    autoFit.current = false;
    setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
  }, []);

  /** Centre the canvas on a point in graph coordinates (used by the overview). */
  const centreOn = useCallback((x, y) => {
    autoFit.current = false;
    setView((v) => ({ ...v, x: size.w / 2 - x * v.k, y: size.h / 2 - y * v.k }));
  }, [size]);

  const moveNode = useCallback((id, x, y) => {
    autoFit.current = false;
    skipAnim.current = true;
    setManual((prev) => ({ ...prev, [id]: { x, y } }));
  }, []);

  /** Forget dragged positions and zoom when a new graph starts. */
  const resetView = useCallback(() => {
    autoFit.current = true;
    setManual({});
  }, []);

  return {
    layout, setLayout,
    positions: display,
    view, size, setSize,
    fit, zoomAt, zoomBy, panBy, centreOn, moveNode, resetView,
  };
}
