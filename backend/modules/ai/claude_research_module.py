"""
Claude OSINT Research Module.

Uses the Anthropic Claude API to generate an AI-driven intelligence profile
for a target individual based on their name, username, and email.

Prompt Customisation
--------------------
Edit the RESEARCH_PROMPT constant below to change what Claude investigates
and how it formats the output.  The module will parse any response that
follows the ``## CATEGORY`` section header format.

Edit MODEL to swap the Claude model used by this module.
Edit MAX_TOKENS to control response length.

Requires
--------
Environment variable ``ANTHROPIC_API_KEY`` must be set before starting the
backend.
"""

import re
from modules.base import BaseModule
from ai.client import get_client


# ── Tuneable constants ─────────────────────────────────────────────────────
# Change MODEL to any valid Anthropic model ID.
MODEL = "claude-haiku-4-5-20251001"

MAX_TOKENS = 2048

# Edit this prompt to change what Claude researches and returns.
# The response must use "## CATEGORY TITLE" headers — the module splits on them.
RESEARCH_PROMPT = """\
You are an OSINT research assistant for spare fishing awareness.
Given a target individual's identifiers, produce a structured intelligence profile
using only information likely to be discoverable through open-source research.

Format your entire response using "## CATEGORY" headers.  Use these sections:

## IDENTITY & BACKGROUND
Full name variations, possible nationality/region based on the name, estimated
age range if inferrable, and any notable public persona.

## LIKELY ONLINE PRESENCE
Platforms this person probably uses based on their username pattern and name.
List as: Platform — likely URL or handle — confidence (High/Medium/Low).

## USERNAME ANALYSIS
Break down the username structure.  Identify any patterns, numbers, or words
that suggest profession, birth year, interests, or naming conventions.
Note other platforms where this exact username may be registered.

## EMAIL INTELLIGENCE
Infer details from the email address: provider choice, username style,
whether it looks personal vs professional, and likely registration era.

## RECOMMENDED SEARCH QUERIES
10 targeted search queries an investigator should run, formatted as a numbered
list.  Cover: full name variants, username across platforms, email dorks,
image search, professional profiles, and forum/community presence.

## EXPOSURE SUMMARY
Show all the relevant information that we could use about the profile, incluiding family and friends if possible.
Provide 3–5 sentence summary of the target's estimated digital footprint, overall
information exposure level (LOW / MEDIUM / HIGH), and the most promising
avenues for further manual investigation.
"""


class ClaudeResearchModule(BaseModule):
    """AI-powered OSINT research module backed by Claude.

    Sends target identifiers to Claude and returns a structured intelligence
    profile broken into labelled sections.  Each section becomes a separate
    result card in the UniThreat UI.
    """

    name = "claude_research"

    def __init__(self):
        self.client = get_client()

    def run(self, target: dict) -> dict:
        """Query Claude with target identifiers and return parsed sections.

        Args:
            target: Dict with keys ``name``, ``username``, ``email``.

        Returns:
            Dict with:
                ``findings`` — list of {category, title, content} dicts.
                ``summary``  — plain-text overview (last section content).
                ``target``   — name string echoed back.
        """
        user_message = self._build_user_message(target)

        message = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=RESEARCH_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = message.content[0].text
        findings = self._parse_sections(raw_text)

        summary = next(
            (f["content"] for f in findings if "SUMMARY" in f["category"].upper()),
            raw_text[:300],
        )

        return {
            "target":   target.get("name", "Unknown"),
            "findings": findings,
            "summary":  summary,
        }

    # ── Private helpers ────────────────────────────────────────────────────

    def _build_user_message(self, target: dict) -> str:
        lines = ["Research the following individual:"]
        if target.get("name"):
            lines.append(f"Full name : {target['name']}")
        if target.get("username"):
            lines.append(f"Username  : {target['username']}")
        if target.get("email"):
            lines.append(f"Email     : {target['email']}")
        lines.append(
            "\nProvide a detailed OSINT intelligence profile using the sections "
            "defined in your instructions."
        )
        return "\n".join(lines)

    def _parse_sections(self, text: str) -> list:
        """Split Claude's response on ## headers into individual finding dicts."""
        sections = re.split(r"(?:^|\n)##\s+", text.strip())
        findings = []

        for section in sections:
            if not section.strip():
                continue
            lines = section.strip().splitlines()
            header  = lines[0].strip().lstrip("#").strip()
            content = "\n".join(lines[1:]).strip()
            if not content:
                continue
            findings.append({
                "category": header,
                "title":    header.title(),
                "content":  content,
            })

        return findings
