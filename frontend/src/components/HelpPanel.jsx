/**
 * HelpPanel.jsx — Help tab in the right dock
 *
 * Two topics, opened from the Help group on the ribbon:
 *   - How to run : setup, starting both servers, what each source needs
 *   - Usage tips : how to get the most out of a run
 *
 * Props:
 *   topic         {string}   - "run" | "tips"
 *   onTopicChange {Function} - Switches the visible topic
 */

const TOPICS = [
  { id: "run",  label: "How to run" },
  { id: "tips", label: "Usage tips" },
];

const REQUIREMENTS = [
  { name: "Google, LinkedIn",  needs: "Google Chrome installed." },
  { name: "Brave",             needs: "BRAVE_API_KEY in backend/.env. Each query uses paid credit." },
  { name: "Claude research, attack vectors", needs: "ANTHROPIC_API_KEY in backend/.env." },
  { name: "Image analysis",    needs: "An uploaded image. The visual analysis also needs ANTHROPIC_API_KEY in backend/.env." },
  { name: "Instagram",         needs: "INSTAGRAM_USERNAME in backend/.env and a saved session (see below)." },
  { name: "Spam checker",      needs: "SpamAssassin installed in WSL." },
  { name: "Other sources",     needs: "No setup needed." },
];

const TROUBLESHOOTING = [
  "If Run analysis shows a network error, check that the backend terminal is still running.",
  "Open the app at http://localhost:5173. The backend rejects requests from any other address.",
  "Restart the backend after changing backend/.env.",
];

const TIP_GROUPS = [
  {
    title: "Get better results",
    tips: [
      "Fill in every field you know. Username and Instagram need an alias, Email OSINT needs an email, and LinkedIn needs a profile URL.",
      "Select the i next to a source to see what it does and what it needs.",
      "DuckDuckGo is a good first source: it's free and needs no setup.",
      "Image search finds pictures linked to a name, username or email, but it can't tell who they show. Check each one before you pin it.",
      "For Image analysis, upload the original file if you can. Social media and messaging apps usually remove location and device data.",
      "Google and LinkedIn open a Chrome window, so keep an eye on it. Solve any Google CAPTCHA within 90 seconds, and sign in to LinkedIn within 5 minutes.",
    ],
  },
  {
    title: "Explore the graph",
    tips: [
      "Drag the background to pan, scroll to zoom, and drag an entity to move it.",
      "Double-click an empty part of the canvas to fit the whole graph in view.",
      "Each source shows its first 24 results. Double-click its collection, or select it and choose Show all, to see the rest.",
      "Type in the filter box to dim entities that don't match. Entity list shows the same results as a table, narrowed to your filter.",
      "Click or drag on the Overview map to move around a large graph.",
      "Using a keyboard? Press Tab to reach an entity, then Enter to select it.",
    ],
  },
  {
    title: "Build your analysis",
    tips: [
      "Pin only the entities that matter. The analysis uses your pinned entities and notes, not the whole graph.",
      "Use Analyst notes for anything the sources missed, such as phone numbers or locations. Notes alone are enough to generate an analysis.",
      "Choose a phishing or social engineering focus for a narrower report.",
      "Copy your analysis before you select New graph. New graph clears your pins, notes and analysis.",
    ],
  },
  {
    title: "When a source fails",
    tips: [
      "A failed source shows a red ! on the graph. Select it to read why it failed, or check the Activity log.",
      "The other sources keep running, so you can still use their results.",
    ],
  },
  {
    title: "Arrange your workspace",
    tips: [
      "Use the View tab to change the layout, switch the graph colour, or hide panels.",
      "Need more room? Hide the ribbon with the arrow at its top right.",
    ],
  },
  {
    title: "Use it responsibly",
    tips: [
      "Only profile people or organizations when you have explicit written permission.",
    ],
  },
];

function Command({ children }) {
  return <pre className="help-command"><code>{children}</code></pre>;
}

function RunTopic() {
  return (
    <>
      <p className="help-intro">
        UniThreat runs as two servers, the backend and the interface. Keep both terminals open while you work.
      </p>

      <section className="help-section">
        <h2 className="panel-title">Before you start</h2>
        <p>Install Python 3.10+, Node.js 18+ and Google Chrome.</p>
      </section>

      <section className="help-section">
        <h2 className="panel-title">1. Set up the backend (first time only)</h2>
        <Command>{"cd backend\npython -m venv .venv\n.venv\\Scripts\\activate\npip install -r requirements.txt"}</Command>
        <p className="dim">On macOS or Linux, activate with: source .venv/bin/activate</p>
        <p>Then copy backend/.env.example to backend/.env and add your API keys.</p>
      </section>

      <section className="help-section">
        <h2 className="panel-title">2. Set up the frontend (first time only)</h2>
        <Command>{"cd frontend\nnpm install"}</Command>
      </section>

      <section className="help-section">
        <h2 className="panel-title">3. Start the backend</h2>
        <p>In a new terminal:</p>
        <Command>{"cd backend\n.venv\\Scripts\\activate\npython app.py"}</Command>
      </section>

      <section className="help-section">
        <h2 className="panel-title">4. Start the frontend</h2>
        <p>In a second terminal:</p>
        <Command>{"cd frontend\nnpm run dev"}</Command>
        <p>Then open <a href="http://localhost:5173">http://localhost:5173</a>.</p>
      </section>

      <section className="help-section">
        <h2 className="panel-title">What each source needs</h2>
        <dl className="property-grid">
          {REQUIREMENTS.map((r) => (
            <div key={r.name} className="property-row">
              <dt>{r.name}</dt>
              <dd>{r.needs}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="help-section">
        <h2 className="panel-title">Save an Instagram session</h2>
        <p>Sign in to Instagram in Chrome. Then run this from backend/, with the virtual environment active:</p>
        <Command>{"python -m instaloader --load-cookies=chrome --login=<your_ig_username>"}</Command>
      </section>

      <section className="help-section">
        <h2 className="panel-title">If something doesn't work</h2>
        <ul className="help-list">
          {TROUBLESHOOTING.map((tip) => <li key={tip}>{tip}</li>)}
        </ul>
      </section>
    </>
  );
}

function TipsTopic() {
  return TIP_GROUPS.map((group) => (
    <section key={group.title} className="help-section">
      <h2 className="panel-title">{group.title}</h2>
      <ul className="help-list">
        {group.tips.map((tip) => <li key={tip}>{tip}</li>)}
      </ul>
    </section>
  ));
}

export default function HelpPanel({ topic, onTopicChange }) {
  return (
    <>
      <div className="view-switch help-switch" role="group" aria-label="Help topic">
        {TOPICS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={topic === t.id ? "active" : ""}
            aria-pressed={topic === t.id}
            onClick={() => onTopicChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {topic === "run" ? <RunTopic /> : <TipsTopic />}
    </>
  );
}
