/**
 * Header.jsx — Application header bar
 *
 * Displays the application brand name and a live status indicator.
 * The status pulses green while gathering or analysing.
 *
 * Props:
 *   statusLabel {string}  - Current status text (e.g. "GATHERING 2/4")
 *   isLive      {boolean} - Animates the status when true
 */
export default function Header({ statusLabel, isLive }) {
  return (
    <header className="header">
      <div className="header-brand">
        UNITHREAT <span>| INTELLIGENCE ENGINE</span>
      </div>

      <div className={`header-status ${isLive ? "live" : ""}`}>
        {statusLabel}
      </div>

      <div className="header-version">v2.0 · Aarhus University</div>
    </header>
  );
}
