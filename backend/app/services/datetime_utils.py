"""Human-readable datetime formatting for brief prompts.

LLMs echo whatever timestamp format they're given verbatim (e.g. raw UTC
ISO strings show up unchanged in generated briefs). Converting to the
user's local timezone and a relative day label here, before the value ever
reaches a prompt, is cheaper and more reliable than asking the model to
reformat it.
"""
from datetime import datetime
from zoneinfo import ZoneInfo


def humanize_datetime(dt: datetime, tz_name: str) -> str:
    """Render dt in the user's local timezone as e.g. 'Today, 3:30 PM' or 'Sun, Jun 28, 10:06 AM'."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")

    local_dt = dt.astimezone(tz)
    today = datetime.now(tz).date()
    delta_days = (local_dt.date() - today).days

    time_str = local_dt.strftime("%I:%M %p").lstrip("0")
    if delta_days == 0:
        return f"Today, {time_str}"
    if delta_days == 1:
        return f"Tomorrow, {time_str}"
    return f"{local_dt.strftime('%a, %b %-d')}, {time_str}"
