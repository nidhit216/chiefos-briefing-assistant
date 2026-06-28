"""Deterministic safety net for the attention_required positive-framing rule.

The prompt instructs the model to frame each entry's third clause as the
positive outcome of acting (e.g. "secures your spot") rather than the
penalty for ignoring it (e.g. "you'll miss the cohort"). Models regress on
this under load even with the rule spelled out, so this catches the
regression in code rather than relying purely on prompt compliance.
"""
import re

_PENALTY_WORDS = re.compile(
    r"\b(missed?|miss|lost|los(e|ing)|delay(ed|s|ing)?|withdraw(n|ing)?|"
    r"revoke[d]?|dissatisfaction|penalt(y|ies)|fail(ed|s|ure)?|"
    r"forfeit(ed)?|expir(ed|es|ing)?)\b",
    re.IGNORECASE,
)

# A penalty word can still appear in a genuinely positive clause, e.g.
# "avoids delays" or "keeps the launch on schedule". Only treat the
# clause as a violation if it has no such positive framing at all.
_POSITIVE_INDICATORS = re.compile(
    r"\b(secures?|keeps?|stays?|opens?|avoids?|prevents?|protects?|"
    r"maintains?|preserves?|saves?|confirms?|books?|locks?|retains?|"
    r"unlocks?|wins?|advances?|strengthens?|on track|on schedule|on time)\b",
    re.IGNORECASE,
)

_FALLBACK_CLAUSE = "handling it now keeps it on track"


def _has_penalty_framing(clause: str) -> bool:
    if _POSITIVE_INDICATORS.search(clause):
        return False
    return bool(_PENALTY_WORDS.search(clause))


def enforce_positive_framing(attention_required: list[str]) -> list[str]:
    """Rewrite any entry whose third clause still reads as a penalty."""
    fixed = []
    for item in attention_required:
        parts = item.split(" — ")
        if len(parts) == 3 and _has_penalty_framing(parts[2]):
            parts[2] = _FALLBACK_CLAUSE
            item = " — ".join(parts)
        fixed.append(item)
    return fixed
