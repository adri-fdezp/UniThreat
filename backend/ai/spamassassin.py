import re
import uuid
import subprocess
from datetime import datetime


def score_email(subject: str, body: str) -> dict:
    """
    Score an email through SpamAssassin running in WSL.
    Returns score, verdict, triggered rules, and a readable summary.
    """
    raw_email = _build_rfc2822(subject, body)
    try:
        result = subprocess.run(
            ["wsl", "spamassassin", "-t"],
            input=raw_email.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        output = result.stdout.decode("utf-8", errors="replace")
        parsed = _parse_output(output)
        if "error" in parsed and result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            parsed["stderr"] = stderr[:500] if stderr else "(empty)"
        return parsed
    except subprocess.TimeoutExpired:
        return {"error": "SpamAssassin timed out", "score": None}
    except FileNotFoundError:
        return {"error": "WSL/SpamAssassin not found on this machine", "score": None}
    except Exception as exc:
        return {"error": str(exc), "score": None}


def _build_rfc2822(subject: str, body: str) -> str:
    """Wrap the email body in RFC 2822 headers SpamAssassin needs.

    Message-ID prevents the MISSING_MID rule.
    Content-Transfer-Encoding: 8bit prevents CTE_8BIT_MISMATCH when the
    body contains non-ASCII characters (common in AI-generated phishing).
    """
    date       = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    message_id = f"<{uuid.uuid4()}@example.com>"
    return (
        f"From: attacker@example.com\r\n"
        f"To: victim@example.com\r\n"
        f"Subject: {subject}\r\n"
        f"Date: {date}\r\n"
        f"Message-ID: {message_id}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=UTF-8\r\n"
        f"Content-Transfer-Encoding: 8bit\r\n"
        f"\r\n"
        f"{body}"
    )


def _parse_output(output: str) -> dict:
    """Parse SpamAssassin's annotated email output into a structured result."""
    score = None
    required = 5.0
    is_spam = False
    rules = []

    # X-Spam-Status: Yes, score=8.3 required=5.0 tests=RULE1,RULE2,...
    status_match = re.search(
        r"X-Spam-Status:\s*(Yes|No),\s*score=([\d.\-]+)\s*required=([\d.]+)\s*tests=([^\r\n]*)",
        output,
        re.IGNORECASE,
    )
    if status_match:
        is_spam  = status_match.group(1).lower() == "yes"
        score    = float(status_match.group(2))
        required = float(status_match.group(3))
        rules    = [r.strip() for r in status_match.group(4).split(",") if r.strip()]

    if score is None:
        return {"error": "Could not parse SpamAssassin output", "score": None, "raw": output[:1500]}

    verdict = "SPAM DETECTED" if is_spam else "PASSES FILTER"

    rule_summary = ", ".join(rules[:8]) + ("…" if len(rules) > 8 else "")

    # X-Spam-Report contains per-rule score + description, folded across lines.
    # Each content line starts with whitespace and looks like:
    #   *  0.0 RULE_NAME   Human readable description
    detailed_rules = []
    report_match = re.search(
        r"X-Spam-Report:\s*\n((?:[ \t]+[^\n]*\n?)*)",
        output,
        re.MULTILINE,
    )
    if report_match:
        for line in report_match.group(1).splitlines():
            m = re.match(r"\s*\*\s*([\d.\-]+)\s+(\S+)\s*(.*)", line)
            if m:
                detailed_rules.append({
                    "score":       float(m.group(1)),
                    "name":        m.group(2),
                    "description": m.group(3).strip(),
                })

    return {
        "score":          score,
        "required":       required,
        "is_spam":        is_spam,
        "verdict":        verdict,
        "rules":          rules,
        "rule_summary":   rule_summary,
        "detailed_rules": detailed_rules,
    }
