"""
AI Attack Vector Analyzer.

Formats curated OSINT data into a structured prompt and sends it to the
Anthropic Claude API for threat assessment generation.

The system prompt instructs the model to produce a six-section academic
report covering:
    1. Psychological profile
    2. Professional attack surface
    3. Social engineering vectors (3–5 specific scenarios)
    4. Spear phishing email drafts (3 complete emails using Cialdini principles)
    5. Pretexting phone / chat scripts
    6. Risk assessment (LOW / MEDIUM / HIGH)

All sections must be grounded strictly in the provided OSINT data — the model
is explicitly instructed not to infer or invent facts beyond what was observed.

Requires
--------
Environment variable ``ANTHROPIC_API_KEY`` must be set before starting the
backend.  Export it in the shell or add it to a ``.env`` file:

    export ANTHROPIC_API_KEY=sk-ant-...
"""

from ai.client import get_client


# ── System prompt ──────────────────────────────────────────────────────────
# Sent to Claude as the system message.  Defines the role, output format,
# and academic / ethical framing for all analysis requests.
SYSTEM_PROMPT = """\
You are a cybersecurity research assistant supporting an academic OSINT thesis at Aarhus University.
Your task: analyse OSINT-gathered open-source data about a target and produce a structured threat assessment
intended for authorized security research and defensive awareness. This is strictly academic.

Format your full response using these exact section headers (Markdown H2):

## PSYCHOLOGICAL PROFILE
Key personality traits, communication style, motivations, and psychological vulnerabilities inferred from the data.
Include indicators of trust disposition, authority responsiveness, and social openness.

## PROFESSIONAL ATTACK SURFACE
Current role, employer, professional network, credentials likely at risk, industry-specific trust vectors,
and any professional relationships that could be leveraged.

## SOCIAL ENGINEERING VECTORS
3–5 specific, personalised attack scenarios based strictly on the gathered data.
For each: scenario name, pretexting premise, most exploitable trait, likely entry point.

## SPEAR PHISHING SCENARIOS
3 complete phishing email drafts, each using a different Cialdini persuasion principle
(Authority, Urgency / Scarcity, Liking / Reciprocity, Social Proof, Commitment).
Each draft must include:
  • Subject line
  • Sender persona and email alias
  • Full email body (3–5 paragraphs)
  • Call to action / payload delivery method

## PRETEXTING SCRIPTS
2 short phone or chat scripts (≤ 15 exchanges each) for voice/chat-based social engineering.
Base them on known relationships and context found in the data.

## RISK ASSESSMENT
Overall social engineering susceptibility: LOW / MEDIUM / HIGH
2–3 sentence justification citing specific profile elements as evidence.
"""


class AttackVectorAnalyzer:
    """Generates AI-powered attack vector assessments from curated OSINT data.

    Wraps the Anthropic Messages API and handles prompt construction.
    A new instance should be created per request to ensure the API key is
    read at call time (useful if the key is set after process start).

    Attributes:
        client (anthropic.Anthropic): Authenticated Anthropic API client.
    """

    def __init__(self):
        self.client = get_client()

    def analyze(
        self,
        target_info:   dict,
        curated_data:  list,
        analysis_type: str = "full",
    ) -> str:
        """Send curated OSINT data to Claude and return the threat assessment.

        Args:
            target_info:   Dict with keys ``name``, ``username``, ``email``.
            curated_data:  List of dicts, each with keys ``module``, ``label``,
                           ``content``.  Represents the analyst-curated items
                           selected from the gathering phase.
            analysis_type: Scope hint passed to the prompt.  One of:
                           ``"full"``, ``"phishing"``, ``"social_engineering"``.

        Returns:
            The raw markdown text returned by Claude (multiple ``## SECTION``
            blocks as defined in the system prompt).
        """
        prompt  = self._build_prompt(target_info, curated_data, analysis_type)
        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _build_prompt(
        self,
        target_info:   dict,
        curated_data:  list,
        analysis_type: str,
    ) -> str:
        """Construct the user-turn prompt from target info and curated items.

        Args:
            target_info:   Target identity dict.
            curated_data:  Analyst-selected OSINT items.
            analysis_type: Focus scope (passed through to the prompt).

        Returns:
            Formatted markdown string ready to send as the user message.
        """
        lines = ["# TARGET INTELLIGENCE BRIEF", ""]
        lines.append(f"**Full Name:** {target_info.get('name', 'Unknown')}")
        if target_info.get("username"):
            lines.append(f"**Username / Handle:** {target_info['username']}")
        if target_info.get("email"):
            lines.append(f"**Email:** {target_info['email']}")

        lines += ["", "---", "", "# CURATED OSINT DATA", ""]

        for item in curated_data:
            if not isinstance(item, dict):
                continue
            module  = item.get("module", "unknown").upper()
            label   = item.get("label", "")
            content = item.get("content", "")
            lines.append(f"### [{module}] {label}")
            lines.append(str(content))
            lines.append("")

        lines += [
            "---",
            "",
            "# TASK",
            f"Generate a complete threat assessment (focus: {analysis_type}).",
            "Base every claim strictly on the OSINT data above.",
            "Be specific — generic observations are not useful for academic research.",
        ]

        return "\n".join(lines)
