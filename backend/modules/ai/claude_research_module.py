# Claude Research Module
# Uses the Claude API to generate an OSINT intelligence profile for a target.
# Claude is given the target's name, username, and email, then asked to reason
# about their likely digital footprint using open-source research techniques.

import re
from modules.base import BaseModule
from ai.client import get_client

# Change MODEL to use a different Claude version
MODEL = "claude-haiku-4-5-20251001"

# Max tokens in Claude's response — increase if the output gets cut off
MAX_TOKENS = 2048

# This is the instruction sent to Claude as a system message.
# Edit the section headers and descriptions to change what Claude researches.
RESEARCH_PROMPT = """\
You are an OSINT research assistant for spear phishing awareness.
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
Show all the relevant information that we could use about the profile, including family and friends if possible.
Provide 3-5 sentence summary of the target's estimated digital footprint, overall
information exposure level (LOW / MEDIUM / HIGH), and the most promising
avenues for further manual investigation.
"""


class ClaudeResearchModule(BaseModule):
    """AI-powered OSINT research using the Claude API."""

    name = "claude_research"

    def __init__(self):
        self.client = get_client()

    def run(self, target: dict) -> dict:
        """Send the target's identifiers to Claude and return the parsed sections."""
        user_message = self._build_user_message(target)

        message = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=RESEARCH_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Find the first text block — Claude can return multiple block types
        raw_text = next(b.text for b in message.content if b.type == "text")
        findings = self._parse_sections(raw_text)

        # Use the Exposure Summary section as the top-level summary card
        summary = next(
            (f["content"] for f in findings if "SUMMARY" in f["category"].upper()),
            raw_text[:300],
        )

        return {
            "target":   target.get("name", "Unknown"),
            "findings": findings,
            "summary":  summary,
        }

    def _build_user_message(self, target: dict) -> str:
        """Format target fields into the user message sent to Claude."""
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
        """Split Claude's response on ## headers into individual result cards."""
        # The regex handles responses that start with ## at the very beginning
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
