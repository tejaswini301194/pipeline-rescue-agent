import json
import re
from datetime import date, datetime
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()

SKILL_TEXT = Path("skills/diagnose_stall.SKILL.md").read_text()

def _json_default(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def _extract_json(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
    return json.loads(cleaned)

def diagnose(deal: dict, history: list[dict]) -> dict:
    """Calls Claude with the skill instructions + deal data, returns a parsed diagnosis."""
    today = date.today().isoformat()

    user_message = f"""
Today's date: {today}

Deal data:
{json.dumps(deal, indent=2, default=_json_default)}

Activity history:
{json.dumps(history, indent=2, default=_json_default)}

Diagnose this deal's stall reason following the skill instructions exactly.
Use today's date above to determine whether expected_close_date is in the past.
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SKILL_TEXT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw_text = response.content[0].text
    return _extract_json(raw_text)
