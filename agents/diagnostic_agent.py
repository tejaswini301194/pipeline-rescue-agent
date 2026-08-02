import json
import re
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()  # reads ANTHROPIC_API_KEY from environment automatically

SKILL_TEXT = Path("skills/diagnose_stall.SKILL.md").read_text()

def _extract_json(raw_text: str) -> dict:
    """Strips markdown code fences if Claude wraps the JSON in them, then parses."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
    return json.loads(cleaned)

def diagnose(deal: dict, history: list[dict]) -> dict:
    """Calls Claude with the skill instructions + deal data, returns a parsed diagnosis."""
    user_message = f"""
Deal data:
{json.dumps(deal, indent=2)}

Activity history:
{json.dumps(history, indent=2)}

Diagnose this deal's stall reason following the skill instructions exactly.
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SKILL_TEXT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw_text = response.content[0].text
    return _extract_json(raw_text)
