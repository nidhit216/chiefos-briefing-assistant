"""Classify incoming emails as low-signal (automated/marketing/digest) so they're
excluded from brief generation context without losing the data entirely."""
import json
import re

from app.config import get_settings
from app.services.ai_client import get_openai_client

settings = get_settings()

# Obvious bulk senders/subjects — caught for free, no LLM call needed.
_NOISE_SENDER_PATTERNS = [
    r"no-?reply@",
    r"do-?not-?reply@",
    r"noreply@",
    r"@ses\.",                    # ← Binance SES and similar AWS SES senders
    r"alerts\.",
    r"alerts@",
    r"notifications@",
    r"mailer@",
    r"@nsdl\.",                   # ← NSDL registrar (BSE postal ballots)
    r"@karvy\.",                  # ← Karvy registrar
    r"@kfintech\.",               # ← KFin Technologies registrar
    r"@evoting\.",                # ← e-voting platforms
    r"@mail\.",                   # ← bulk mail subdomains (mail.michaelpage etc)
    r"reply\.cutshort\.io",       # ← Cutshort automated recruiter replies
    r"@cutshort\.io",
    r"@linkedin\.com",
    r"@glassdoor\.com",
    r"@naukri\.com",
]

_NOISE_SUBJECT_PATTERNS = [
    r"new jobs for:",
    r"invited you to apply",
    r"update your kyc",
    r"verify your account",
    r"questionnaire.*pending",
    r"postal ballot",             # ← BSE/registrar voting notices
    r"e-?voting",                 # ← all e-voting notices
    r"remote e-?voting",
    r"annual general meeting",
    r"\bagm\b",
    r"login from a new device",   # ← Notion/platform security alerts
    r"new sign.?in",
    r"new login",
    r"security alert",
    r"new device",
    r"someone signed in",
    r"account (access|security|verification)",
    r"complete your kyc",
    r"update.*kyc",
    r"reminder.*kyc",
]


def matches_noise_heuristic(sender: str, subject: str) -> bool:
    sender_l = sender.lower()
    subject_l = subject.lower()
    return any(re.search(p, sender_l) for p in _NOISE_SENDER_PATTERNS) or any(
        re.search(p, subject_l) for p in _NOISE_SUBJECT_PATTERNS
    )


async def classify_low_signal(candidates: list[dict]) -> dict[int, bool]:
    """Batch-classify emails the heuristic didn't already catch.

    candidates: list of {"sender", "subject", "snippet"}. Returns {index: is_low_signal}
    keyed by position in `candidates`. Fails open (empty dict, i.e. treat as NOT
    low-signal) on any error so a transient AI outage never hides a real email.
    """
    if not candidates:
        return {}

    prompt_items = "\n".join(
        f"{i}. From: {c['sender']} | Subject: {c['subject']} | Snippet: {c['snippet'][:200]}"
        for i, c in enumerate(candidates)
    )

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.ai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are classifying emails for a personal chief of staff app. "
                        "Be aggressive about marking things low_signal. "
                        "ALWAYS mark as low_signal: e-voting notices, postal ballots, "
                        "AGM notices, KYC reminders, new device/login security alerts from "
                        "platforms (Notion, GitHub, Google, Binance etc), job board digests, "
                        "recruiter mass outreach, newsletter-style updates from companies. "
                        "Only mark 'actionable' if a named individual who knows this person "
                        "personally is waiting on a specific reply or decision. "
                        "When in doubt, mark low_signal. "
                        'Respond ONLY with JSON: {"results": [{"index": 0, "type": "low_signal"}]}'
                    ),
                },
                {"role": "user", "content": prompt_items},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content)
        return {
            int(r["index"]): r.get("type") == "low_signal"
            for r in data.get("results", [])
        }
    except Exception:
        return {}
