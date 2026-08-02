from dotenv import load_dotenv
load_dotenv()

from core.db import get_connection
from agents.diagnostic_agent import diagnose

# Correct labels, hand-verified: both deals have expected_close_date in the past
# (today is 2026-08-02), so PAST_DUE_CLOSE_DATE is the objectively correct answer
# per the priority rule now in the skill file.
test_cases = [
    {"deal_id": 1, "expected_reason": "PAST_DUE_CLOSE_DATE"},  # Acme Corp, close date 2026-07-01
    {"deal_id": 3, "expected_reason": "PAST_DUE_CLOSE_DATE"},  # Globex LLC, close date 2026-06-20
]

def diagnose_by_id(deal_id: int) -> dict:
    conn = get_connection()
    deal = dict(conn.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,)).fetchone())
    history = [dict(h) for h in conn.execute(
        "SELECT * FROM activity_log WHERE deal_id = ?", (deal_id,)
    ).fetchall()]
    conn.close()
    return diagnose(deal, history)

def evaluate(test_cases):
    correct = 0
    for case in test_cases:
        result = diagnose_by_id(case["deal_id"])
        is_correct = result["stall_reason"] == case["expected_reason"]
        correct += is_correct
        print(f"deal_id {case['deal_id']}: expected={case['expected_reason']} "
              f"got={result['stall_reason']} confidence={result['confidence']:.0%} "
              f"{'✓' if is_correct else '✗'}")
    accuracy = correct / len(test_cases)
    print(f"\nDiagnostic accuracy: {accuracy:.0%} ({correct}/{len(test_cases)})")

if __name__ == "__main__":
    evaluate(test_cases)
