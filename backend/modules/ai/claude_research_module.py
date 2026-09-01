# Claude Research Module
# Uses the Claude API to generate an OSINT intelligence profile for a target.
# Claude is given the target's name, username, and email, then asked to reason
# about their likely digital footprint using open-source research techniques.

import re
from anthropic.types import WebSearchTool20260209Param
from modules.base import BaseModule
from ai.client import get_client

# Change MODEL to use a different Claude version
MODEL = "claude-sonnet-5"

# Max tokens in Claude's response — increase if the output gets cut off.
# Raised from the original 4096 because web search results (and the
# "SEARCHES PERFORMED" section reporting on them) consume extra tokens.
MAX_TOKENS = 16000

# Claude's built-in web_search tool. `web_search_20260209` adds dynamic
# filtering (Claude writes/executes code to filter results before they hit
# the context window) — available on Sonnet 5, but not on Haiku, which is
# why the module previously had to use the older basic variant.
WEB_SEARCH_TOOL: WebSearchTool20260209Param = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 8,
}

# This is the instruction sent to Claude as a system message.
# Edit the section headers and descriptions to change what Claude researches.
RESEARCH_PROMPT = """\
You are an OSINT research assistant for spear phishing awareness, operating in
an authorized security assessment. You have a `web_search` tool — use it.

Before writing any findings, run multiple targeted searches: the full name
(with quotes and variations), the username across platforms, the email address
and its local-part, and combinations of these with terms like "linkedin",
"github", "instagram", "resume", "profile". Do not write a single section
before you have searched for it.

Every claim you make must be labeled with its provenance:
- "Confirmed (source: <url>)" — you found this in an actual search result.
  Never write a Confirmed claim without a real URL from a tool result backing it.
- "Inferred" — you are pattern-matching from the name/username/email
  structure itself, not from a search result. Say so explicitly.
If a search turns up nothing relevant, say "No public results found" rather
than filling the gap with a plausible-sounding guess. Do not invent URLs,
usernames, or handles that did not appear in an actual search result.

Format your entire response using "## CATEGORY" headers. Use these sections:

## IDENTITY & BACKGROUND
Full name variations, possible nationality/region based on the name, estimated
age range if inferrable, and any notable public persona. Mark each item
Confirmed (with source) or Inferred.

## LIKELY ONLINE PRESENCE
Platforms this person uses. List as: Platform — URL or handle — Confirmed/Inferred
— confidence (High/Medium/Low). Confirmed entries must cite the search result
they came from; do not list a profile as Confirmed unless you actually saw it
in a search result.

## USERNAME ANALYSIS
Break down the username structure: patterns, numbers, or words that suggest
profession, birth year, interests, or naming conventions. This section is
necessarily Inferred (pattern reasoning), unless a search directly confirms one
of these guesses — say so if it does. Note other platforms where this exact
username turned up in search.

## EMAIL INTELLIGENCE
Infer details from the email address: provider choice, username style,
whether it looks personal vs professional, and likely registration era. Also
Inferred unless a search result (e.g. a breach notice or public listing)
confirms something.

## SEARCHES PERFORMED
List the actual search queries you ran via the web_search tool, one per line,
and one sentence on what each returned (or "no relevant results"). Then add up
to 5 additional queries an investigator could run next that you did not have
budget to try, covering angles you haven't covered yet.

## EXPOSURE SUMMARY
Summarize only what search actually surfaced — do not speculate about family
or associates unless a search result explicitly named them with a source.
Provide a 3-5 sentence summary of the target's estimated digital footprint,
overall information exposure level (LOW / MEDIUM / HIGH), and the most
promising avenues for further manual investigation.
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
            system=[
                {
                    "type": "text",
                    "text": RESEARCH_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": user_message}],
        )

        # With web_search enabled, Claude's reply is interleaved text/tool-use/
        # tool-result blocks — concatenate every text block, not just the first.
        raw_text = "\n".join(b.text for b in message.content if b.type == "text")
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
