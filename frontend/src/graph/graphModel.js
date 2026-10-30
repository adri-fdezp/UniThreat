/**
 * graphModel.js — Turns the target and flattened results into a node/link graph
 *
 * This is presentation only: it reads the same flat items the result list uses
 * and never changes what a module returns.
 *
 * Shape of the graph:
 *   person (root) → known identifiers (username, email, LinkedIn URL)
 *   person (root) → one hub per selected module → one entity per result
 */

// Hubs with more results than this show a "+N more" collection until expanded
const HUB_LIMIT = 24;

/** Pick the entity icon for a result based on where it came from. */
function iconForItem(item) {
  switch (item.module) {
    case "instagram":
      return item.category === "Post" ? "post" : "profile";
    case "linkedin":
      if (item.category === "Timeline") return "timeline";
      return item.category === "Recent Posts" ? "post" : "profile";
    case "username_enum":
      return "alias";
    case "email_osint":
      return item.category === "Gravatar" ? "profile" : "email";
    case "claude_research":
      return "document";
    case "image_search":
      return "image";
    case "image_analysis":
      return "document";
    default:
      return item.url ? "website" : "document";
  }
}

/** Build the node for one result item. */
export function entityNode(item) {
  return {
    id:     `e_${item.id}`,
    kind:   "entity",
    icon:   iconForItem(item),
    label:  item.title,
    module: item.module,
    parent: `hub_${item.module}`,
    item,
  };
}

/**
 * Return the URL only if it is a normal web link, otherwise "".
 * Result URLs come from scraped pages, so a javascript: link must never become clickable.
 */
export function safeUrl(url) {
  try {
    const { protocol } = new URL(url);
    return protocol === "http:" || protocol === "https:" ? url : "";
  } catch {
    return "";
  }
}

/** True when an item matches the quick-find text. */
export function matchesFilter(item, text) {
  const q = text.trim().toLowerCase();
  if (!q) return true;
  return (
    item.title.toLowerCase().includes(q)    ||
    item.category.toLowerCase().includes(q) ||
    item.content.toLowerCase().includes(q)  ||
    item.url.toLowerCase().includes(q)
  );
}

/**
 * @param {object} args
 * @param {object} args.target    - { name, username, email, linkedin_url }
 * @param {Array}  args.items     - Flattened result items
 * @param {Array}  args.modules   - Selected modules as { id, label, note }
 * @param {object} args.statuses  - Module id → pending | running | done | error
 * @param {object} args.errors    - Module id → error message
 * @param {Array}  args.expanded  - Module ids whose collections are expanded
 * @returns {{nodes: Array, edges: Array}}
 */
export function buildGraph({ target, items, modules, statuses, errors, expanded }) {
  if (!target?.name) return { nodes: [], edges: [] };

  const nodes = [{ id: "root", kind: "person", icon: "person", label: target.name, target }];
  const edges = [];

  const addChild = (node, from, label = "") => {
    nodes.push({ ...node, parent: from });
    edges.push({ id: `${from}>${node.id}`, from, to: node.id, label });
  };

  if (target.username)
    addChild({ id: "id_username", kind: "identifier", icon: "alias", label: `@${target.username.replace(/^@/, "")}` }, "root", "Username");
  if (target.email)
    addChild({ id: "id_email", kind: "identifier", icon: "email", label: target.email }, "root", "Email");
  if (target.linkedin_url)
    addChild(
      { id: "id_linkedin", kind: "identifier", icon: "website", label: target.linkedin_url.replace(/^https?:\/\/(www\.)?/, "") },
      "root",
      "LinkedIn URL",
    );

  modules.forEach((mod) => {
    const own    = items.filter((item) => item.module === mod.id);
    const shown  = expanded.includes(mod.id) ? own : own.slice(0, HUB_LIMIT);
    const hidden = own.length - shown.length;
    const hubId  = `hub_${mod.id}`;

    addChild(
      {
        id:     hubId,
        kind:   "hub",
        icon:   `mod_${mod.id}`,
        label:  mod.label,
        module: mod.id,
        note:   mod.note,
        status: statuses[mod.id] || "pending",
        error:  errors[mod.id] || "",
        count:  own.length,
        hidden,
      },
      "root",
    );

    shown.forEach((item) => {
      const node = entityNode(item);
      addChild(node, hubId, item.category);
    });

    if (hidden > 0) {
      addChild(
        { id: `${hubId}_more`, kind: "more", icon: "collection", label: `${hidden} more`, module: mod.id, hidden },
        hubId,
      );
    }
  });

  return { nodes, edges };
}

/** Group nodes by parent id. */
function childrenByParent(nodes) {
  const kids = {};
  nodes.forEach((n) => {
    if (n.parent) (kids[n.parent] = kids[n.parent] || []).push(n);
  });
  return kids;
}

/** Person in the centre, hubs on a ring, results fanning outward in rows. */
function circular({ nodes }) {
  const pos = {};
  if (!nodes.length) return pos;
  pos.root = { x: 0, y: 0 };

  const kids   = childrenByParent(nodes);
  const first  = kids.root || [];
  const weight = (n) => 2 + Math.sqrt(kids[n.id]?.length || 0);
  const total  = first.reduce((sum, n) => sum + weight(n), 0);
  const ring   = Math.max(210, (first.length * 120) / (2 * Math.PI));
  const gap    = 104; // distance between neighbours along an arc

  let angle = -Math.PI / 2;
  first.forEach((n) => {
    const span = (2 * Math.PI * weight(n)) / total;
    const mid  = angle + span / 2;
    pos[n.id]  = { x: Math.cos(mid) * ring, y: Math.sin(mid) * ring };

    const children = kids[n.id] || [];
    let radius = ring + 170;
    let placed = 0;
    while (placed < children.length) {
      const capacity = Math.max(1, Math.floor((span * 0.92 * radius) / gap));
      const row = children.slice(placed, placed + capacity);
      const r = radius;
      row.forEach((child, i) => {
        const a = mid + (i - (row.length - 1) / 2) * (gap / r);
        pos[child.id] = { x: Math.cos(a) * r, y: Math.sin(a) * r };
      });
      placed += row.length;
      radius += 112;
    }
    angle += span;
  });
  return pos;
}

/** Top-down tree: person, then a row of hubs, then each hub's results beneath it. */
function hierarchical({ nodes }) {
  const pos = {};
  if (!nodes.length) return pos;

  const kids   = childrenByParent(nodes);
  const first  = kids.root || [];
  const step   = 122;
  const blocks = first.map((n) => {
    const count = kids[n.id]?.length || 0;
    const cols  = Math.max(1, Math.min(7, Math.ceil(Math.sqrt(count * 1.6))));
    return { node: n, cols, width: cols * step };
  });

  const totalWidth = blocks.reduce((sum, b) => sum + b.width, 0);
  let x = -totalWidth / 2;
  pos.root = { x: 0, y: 0 };

  blocks.forEach(({ node, cols, width }) => {
    const centre = x + width / 2;
    pos[node.id] = { x: centre, y: 180 };
    (kids[node.id] || []).forEach((child, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      pos[child.id] = {
        x: centre + (col - (cols - 1) / 2) * step,
        y: 340 + row * 112,
      };
    });
    x += width;
  });
  return pos;
}

/** Everything on one even grid, kept in module order. */
function block({ nodes }) {
  const pos = {};
  if (!nodes.length) return pos;

  const kids = childrenByParent(nodes);
  const ordered = [nodes[0]];
  (kids.root || []).forEach((n) => {
    ordered.push(n, ...(kids[n.id] || []));
  });

  const cols = Math.ceil(Math.sqrt(ordered.length * 1.5));
  ordered.forEach((n, i) => {
    pos[n.id] = { x: (i % cols) * 128, y: Math.floor(i / cols) * 112 };
  });
  return pos;
}

export const LAYOUTS = { block, hierarchical, circular };

/** Work out the pan and zoom that fits every node in the canvas. */
export function fitView(positions, size) {
  const points = Object.values(positions);
  if (!points.length || !size.w || !size.h) return { x: size.w / 2 || 0, y: size.h / 2 || 0, k: 1 };

  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs) - 90;
  const maxX = Math.max(...xs) + 90;
  const minY = Math.min(...ys) - 70;
  const maxY = Math.max(...ys) + 90;

  const k = Math.max(0.08, Math.min(size.w / (maxX - minX), size.h / (maxY - minY), 1.15));
  return {
    x: size.w / 2 - (k * (minX + maxX)) / 2,
    y: size.h / 2 - (k * (minY + maxY)) / 2,
    k,
  };
}
