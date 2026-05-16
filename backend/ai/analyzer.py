# AI Threat Analyzer
# Takes the OSINT data the analyst pinned and sends it to Claude.
# Claude returns a structured threat report with phishing scenarios,
# social engineering vectors, and a risk rating.

from ai.client import get_anthropic_client, get_gemini_client

# System prompt that tells the AI what role to play and how to format the output.
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
    """Sends curated OSINT data to Claude or Gemini and returns a threat assessment report."""

    def analyze(self, target_info: dict, curated_data: list, analysis_type: str = "full", provider: str = "claude") -> str:
        """Build the prompt and call the selected AI API."""
        prompt = self._build_prompt(target_info, curated_data, analysis_type)
        
        if provider == "gemini":
            return self._analyze_gemini(prompt)
        else:
            return self._analyze_claude(prompt)

    def _analyze_claude(self, prompt: str) -> str:
        """Call the Anthropic Claude API."""
        client = get_anthropic_client()
        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _analyze_gemini(self, prompt: str) -> str:
        """Call the Google Gemini API."""
        genai = get_gemini_client()
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT
        )
        response = model.generate_content(prompt)
        return response.text

    def _build_prompt(self, target_info: dict, curated_data: list, analysis_type: str) -> str:
        """Format the target info and pinned OSINT cards into a single prompt."""
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
