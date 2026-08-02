import json
import re
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()
SKILL_TEXT = Path("skills/recommend_action.SKILL.md").read_text()

def _extract_json(raw_text: str) -> dict:
    """Strips markdown code fences if Claude wraps the JSON in them, then parses."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
    return json.loads(cleaned)

def recommend(diagnosis: dict) -> dict:
    user_message = f"""
Diagnosis:
{json.dumps(diagnosis, indent=2)}

Recommend one rescue action following the skill instructions exactly.
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=SKILL_TEXT,
        messages=[{"role": "user", "content": user_message}],
    )
    return _extract_json(response.content[0].text)
