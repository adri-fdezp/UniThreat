/**
 * Icons.jsx — Entity pictograms for the graph and line icons for the ribbon
 *
 * All drawn for this project as inline SVG.  Module hubs use generic pictures
 * (a magnifier, a camera) rather than the logos of the services they query.
 */

// Hexagon behind each module hub, tinted per module
const hex = (fill) => <path d="M24 2.5 43 13.2v21.6L24 45.5 5 34.8V13.2Z" fill={fill} />;
const hexGlyph = "#ffffff";

const magnifier = (
  <>
    <circle cx="21.5" cy="21.5" r="7.5" fill="none" stroke={hexGlyph} strokeWidth="3" />
    <path d="m27 27 7 7" stroke={hexGlyph} strokeWidth="3.4" strokeLinecap="round" />
  </>
);

const ENTITY_ICONS = {
  person: (
    <>
      <circle cx="24" cy="15" r="9.5" fill="#5db2ee" />
      <path d="M6 44c0-11 8-17.5 18-17.5S42 33 42 44Z" fill="#2f86cf" />
      <path d="M17 12.5a9.5 9.5 0 0 1 13-2.6" fill="none" stroke="#bfe2fb" strokeWidth="2" strokeLinecap="round" />
    </>
  ),
  alias: (
    <>
      <rect x="5" y="11" width="38" height="27" rx="3.5" fill="#8d6fd8" />
      <rect x="5" y="11" width="38" height="7" rx="3" fill="#6d50b8" />
      <circle cx="16" cy="26" r="4.2" fill="#e7defc" />
      <path d="M9.5 34.5c.6-3.6 3.2-5.2 6.5-5.2s5.9 1.6 6.5 5.2Z" fill="#e7defc" />
      <path d="M27 24.5h11M27 30h8" stroke="#e7defc" strokeWidth="2.4" strokeLinecap="round" />
    </>
  ),
  email: (
    <>
      <rect x="4" y="11" width="40" height="27" rx="3" fill="#eeb23f" />
      <path d="m5 13 19 14.5L43 13" fill="none" stroke="#a66e0c" strokeWidth="2.6" strokeLinejoin="round" />
      <path d="m5 37 13.5-13M43 37 29.5 24" stroke="#c98d1f" strokeWidth="2" />
    </>
  ),
  website: (
    <>
      <circle cx="24" cy="24" r="19" fill="#3fa76a" />
      <g fill="none" stroke="#d7f3e2" strokeWidth="2">
        <ellipse cx="24" cy="24" rx="8.5" ry="19" />
        <path d="M5 24h38M8 14h32M8 34h32" />
      </g>
    </>
  ),
  document: (
    <>
      <path d="M10 3.5h19l10 10V44.5H10Z" fill="#e4e8ec" />
      <path d="M29 3.5v10h10Z" fill="#a9b3bd" />
      <path d="M16 20h17M16 26h17M16 32h17M16 38h10" stroke="#65727e" strokeWidth="2.2" strokeLinecap="round" />
    </>
  ),
  image: (
    <>
      <rect x="4" y="8" width="40" height="32" rx="3.5" fill="#d9825b" />
      <circle cx="16" cy="18" r="4" fill="#fbe6da" />
      <path d="M8 36 19 25l7 7 6-6 8 10Z" fill="#fbe6da" />
    </>
  ),
  post: (
    <>
      <path d="M6 7h36a2 2 0 0 1 2 2v24a2 2 0 0 1-2 2H22l-9 9v-9H6a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z" fill="#dd5f93" />
      <path d="M12 16h24M12 22h24M12 28h15" stroke="#fde3ee" strokeWidth="2.4" strokeLinecap="round" />
    </>
  ),
  profile: (
    <>
      <rect x="4" y="8" width="40" height="32" rx="3.5" fill="#2fa2a5" />
      <circle cx="17" cy="20" r="5.5" fill="#d6f3f3" />
      <path d="M8 34.5c.8-5 4.5-7.2 9-7.2s8.2 2.2 9 7.2Z" fill="#d6f3f3" />
      <path d="M30 18h9M30 24h9M30 30h6" stroke="#d6f3f3" strokeWidth="2.4" strokeLinecap="round" />
    </>
  ),
  timeline: (
    <>
      <rect x="4" y="6" width="40" height="36" rx="3.5" fill="#5a7bc9" />
      <path d="M14 13v22" stroke="#dbe5fb" strokeWidth="2.4" />
      <g fill="#dbe5fb">
        <circle cx="14" cy="15" r="3" />
        <circle cx="14" cy="24" r="3" />
        <circle cx="14" cy="33" r="3" />
      </g>
      <path d="M21 15h16M21 24h12M21 33h15" stroke="#dbe5fb" strokeWidth="2.4" strokeLinecap="round" />
    </>
  ),
  collection: (
    <>
      <rect x="13" y="6" width="30" height="24" rx="3" fill="#6e7780" />
      <rect x="9" y="12" width="30" height="24" rx="3" fill="#8c959e" />
      <rect x="5" y="18" width="30" height="24" rx="3" fill="#b4bcc4" />
      <path d="M20 24v12M14 30h12" stroke="#3f464d" strokeWidth="2.8" strokeLinecap="round" />
    </>
  ),
  mod_google: <>{hex("#bd8f12")}{magnifier}</>,
  mod_duckduckgo: <>{hex("#d4692a")}{magnifier}</>,
  mod_brave: <>{hex("#5f7d2e")}{magnifier}</>,
  mod_image_search: (
    <>
      {hex("#b5623a")}
      <circle cx="21.5" cy="21.5" r="8" fill="none" stroke={hexGlyph} strokeWidth="3" />
      <path d="m27.500 27.500 6.500 6.500" stroke={hexGlyph} strokeWidth="3.400" strokeLinecap="round" />
      <path d="m16.500 24.500 3.500-3.500 2 2 1.500-1.500 2 3" fill="none" stroke={hexGlyph} strokeWidth="1.800" strokeLinejoin="round" />
    </>
  ),
  mod_image_analysis: (
    <>
      {hex("#8f4f7a")}
      <rect x="12.500" y="15" width="23" height="18" rx="2" fill="none" stroke={hexGlyph} strokeWidth="2.600" />
      <circle cx="19" cy="21" r="2.200" fill={hexGlyph} />
      <path d="m15.500 30.500 6-6 3.500 3.500 3-3 4.500 5.500" fill="none" stroke={hexGlyph} strokeWidth="2.200" strokeLinejoin="round" />
    </>
  ),
  mod_instagram: (
    <>
      {hex("#b5458f")}
      <rect x="13" y="15" width="22" height="18" rx="3" fill="none" stroke={hexGlyph} strokeWidth="2.6" />
      <circle cx="24" cy="24" r="4.6" fill="none" stroke={hexGlyph} strokeWidth="2.6" />
    </>
  ),
  mod_linkedin: (
    <>
      {hex("#2d73b5")}
      <rect x="13" y="19" width="22" height="15" rx="2" fill={hexGlyph} />
      <path d="M19.5 19v-3a2 2 0 0 1 2-2h5a2 2 0 0 1 2 2v3" fill="none" stroke={hexGlyph} strokeWidth="2.4" />
      <path d="M13 25.5h22" stroke="#2d73b5" strokeWidth="2" />
    </>
  ),
  mod_username_enum: (
    <>
      {hex("#7555c4")}
      <circle cx="24" cy="24" r="4.4" fill="none" stroke={hexGlyph} strokeWidth="2.6" />
      <path d="M28.4 19.6V26a3 3 0 0 0 6 0v-2a10.4 10.4 0 1 0-4.6 8.6" fill="none" stroke={hexGlyph} strokeWidth="2.6" strokeLinecap="round" />
    </>
  ),
  mod_email_osint: (
    <>
      {hex("#c2483f")}
      <rect x="12.5" y="16" width="23" height="16" rx="2" fill="none" stroke={hexGlyph} strokeWidth="2.6" />
      <path d="m13.5 17.5 10.5 8 10.5-8" fill="none" stroke={hexGlyph} strokeWidth="2.6" />
    </>
  ),
  mod_claude_research: (
    <>
      {hex("#23887f")}
      <path d="M24 12.5c1.2 7 4.5 10.3 11.5 11.5-7 1.2-10.3 4.5-11.5 11.5-1.2-7-4.5-10.3-11.5-11.5 7-1.2 10.3-4.5 11.5-11.5Z" fill={hexGlyph} />
    </>
  ),
};

// Dot colours used when the graph is zoomed too far out to show pictures
export const ICON_COLOURS = {
  person: "#5db2ee", alias: "#8d6fd8", email: "#eeb23f", website: "#3fa76a",
  document: "#c5ccd3", post: "#dd5f93", profile: "#2fa2a5", timeline: "#5a7bc9",
  collection: "#8c959e", mod_google: "#bd8f12", mod_duckduckgo: "#d4692a", mod_brave: "#5f7d2e",
  mod_instagram: "#b5458f", mod_linkedin: "#2d73b5", mod_username_enum: "#7555c4",
  mod_email_osint: "#c2483f", mod_claude_research: "#23887f",
  image: "#d9825b", mod_image_search: "#b5623a", mod_image_analysis: "#8f4f7a",
};

/** Entity pictogram.  Works inside HTML, or inside another SVG using x and y. */
export function EntityIcon({ name, size = 24, x, y }) {
  return (
    <svg width={size} height={size} x={x} y={y} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      {ENTITY_ICONS[name] || ENTITY_ICONS.document}
    </svg>
  );
}

const UI_ICONS = {
  run: <path d="M6 3.5v13l10.5-6.5Z" fill="currentColor" stroke="none" />,
  newGraph: <path d="M5 2.5h7l3.5 3.5v11.5H5Zm5 7v5M7.5 12h5" />,
  star: <path d="m10 2.5 2.3 4.9 5.3.7-3.9 3.7 1 5.3L10 14.5l-4.7 2.6 1-5.3L2.400 8.100l5.300-.7Z" />,
  link: <path d="M8 12l4-4M9 5.500l1.600-1.600a3.200 3.200 0 0 1 4.500 4.500L13.500 10M11 14.500l-1.600 1.600a3.200 3.200 0 0 1-4.500-4.500L6.500 10" />,
  expand: <path d="M3 8V3h5M17 12v5h-5M3 3l5.500 5.500M17 17l-5.500-5.500" />,
  workspace: <path d="M3 3.500h14v13H3ZM3 7.500h14M8 7.500v9" />,
  mail: <path d="M2.500 5h15v10.500h-15ZM3 5.500l7 5.500 7-5.500" />,
  terminal: <path d="M3 3.500h14v13H3ZM6 7.500 9 10l-3 2.500M10.500 12.500H14" />,
  lightbulb: <path d="M10 2.500a5 5 0 0 0-3 9c.6.500 1 1.100 1 1.900v.100h4v-.100c0-.800.400-1.400 1-1.900a5 5 0 0 0-3-9ZM8 16h4M9 17.800h2" />,
  block: <path d="M3 3h4v4H3Zm5 0h4v4H8Zm5 0h4v4h-4ZM3 8h4v4H3Zm5 0h4v4H8Zm5 0h4v4h-4ZM3 13h4v4H3Zm5 0h4v4H8Z" />,
  hierarchical: <path d="M8 2.500h4v3.500H8ZM2.500 14h4v3.500h-4Zm5.500 0h4v3.500H8Zm5.500 0h4v3.500h-4ZM10 6v8M4.500 14v-3.500h11V14" />,
  circular: <path d="M10 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM10 2.500v3M10 14.500v3M2.500 10h3M14.500 10h3M4.700 4.700l2.100 2.100M13.200 13.200l2.100 2.100M15.300 4.700l-2.100 2.100M6.800 13.200l-2.100 2.100" />,
  zoomIn: <path d="M8.500 3a5.500 5.500 0 1 0 0 11 5.500 5.500 0 0 0 0-11ZM12.500 12.500 17 17M8.500 6v5M6 8.500h5" />,
  zoomOut: <path d="M8.500 3a5.500 5.500 0 1 0 0 11 5.500 5.500 0 0 0 0-11ZM12.500 12.500 17 17M6 8.500h5" />,
  fit: <path d="M3 7V3h4M13 3h4v4M17 13v4h-4M7 17H3v-4M7 7h6v6H7Z" />,
  canvas: <path d="M3 3.500h14v13H3ZM10 3.500v13M10 7l7-3.500M10 11l7-3.500M10 15l7-3.500" />,
  palette: <path d="M3 3.500h14v13H3ZM8 3.500v13" />,
  dock: <path d="M3 3.500h14v13H3ZM12 3.500v13" />,
  output: <path d="M3 3.500h14v13H3ZM3 12h14" />,
  graphView: (
    <>
      <circle cx="10" cy="4.500" r="2.250" />
      <circle cx="4.500" cy="15" r="2.250" />
      <circle cx="15.500" cy="15" r="2.250" />
      <path d="M8.960 6.490 5.540 13M11.040 6.490 14.460 13M6.750 15h6.500" />
    </>
  ),
  listView: <path d="M3 4.500h14M3 8.500h14M3 12.500h14M3 16.500h14" />,
  chevronUp: <path d="m5 12.500 5-5 5 5" />,
  chevronDown: <path d="m5 7.500 5 5 5-5" />,
};

/** Monochrome line icon that takes its colour from the surrounding text. */
export function UiIcon({ name, size = 18, filled = false }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {UI_ICONS[name]}
    </svg>
  );
}
