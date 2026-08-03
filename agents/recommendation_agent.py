import json
import re
from datetime import date, datetime
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()
SKILL_TEXT = Path("skills/recommend_action.SKILL.md").read_text()

def _json_default(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def _extract_json(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
    return json.loads(cleaned)

def recommend(diagnosis: dict) -> dict:
    user_message = f"""
Diagnosis:
{json.dumps(diagnosis, indent=2, default=_json_default)}

Recommend one rescue action following the skill instructions exactly.
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=SKILL_TEXT,
        messages=[{"role": "user", "content": user_message}],
    )
    return _extract_json(response.content[0].text)
