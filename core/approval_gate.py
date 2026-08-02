from rich.console import Console
from rich.prompt import Confirm
from core.db import get_connection
from datetime import datetime

console = Console()

def request_human_approval(deal: dict, diagnosis: dict, recommendation: dict) -> bool:
    """
    Shows the human everything the agents concluded, and BLOCKS until
    the human types y/n. Nothing downstream runs without this.
    """
    console.rule(f"Approval needed -- {deal['account_name']}")
    console.print(f"Deal value: ${deal['deal_value']:,.0f}   Stage: {deal['stage']}")
    console.print(f"Diagnosis: {diagnosis['stall_reason']} "
                   f"(confidence {diagnosis['confidence']:.0%})")
    console.print(f"Reasoning: {diagnosis['reasoning']}")
    console.print(f"Proposed action: {recommendation['recommended_action']}")
    console.print(f"Urgency: {recommendation['urgency']}")

    approved = Confirm.ask("Approve this action?", default=False)

    conn = get_connection()
    conn.execute("""
        INSERT INTO approvals (deal_id, proposed_action, status, reviewed_by, reviewed_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        deal["deal_id"],
        recommendation["recommended_action"],
        "approved" if approved else "rejected",
        "human_reviewer",
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()

    return approved
