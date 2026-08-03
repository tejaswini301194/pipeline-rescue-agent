from core.db import init_db, get_connection
from agents.diagnostic_agent import diagnose
from agents.recommendation_agent import recommend

def scan_and_propose(days_since_contact: int = 14) -> list[dict]:
    """
    Non-blocking version of the pipeline for API use.
    Diagnoses + recommends for every stalled deal, writes a PENDING
    approval row for each one, and returns immediately -- no waiting
    on a human. A human decides later via decide_approval().
    """
    init_db()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM deals
                WHERE status = 'open'
                AND CURRENT_DATE - last_contacted_date >= %s
            """, (days_since_contact,))
            stalled = cur.fetchall()

    created = []

    for deal in stalled:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM activity_log WHERE deal_id = %s", (deal["deal_id"],)
                )
                history = cur.fetchall()

        diagnosis = diagnose(deal, history)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
                    VALUES (%s, 'DiagnosticAgent', 'diagnosed', %s, NOW())
                """, (deal["deal_id"], diagnosis["stall_reason"]))
            conn.commit()

        recommendation = recommend(diagnosis)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO approvals (deal_id, proposed_action, status)
                    VALUES (%s, %s, 'pending')
                    RETURNING approval_id
                """, (deal["deal_id"], recommendation["recommended_action"]))
                approval_id = cur.fetchone()["approval_id"]
            conn.commit()

        created.append({
            "approval_id": approval_id,
            "deal_id": deal["deal_id"],
            "account_name": deal["account_name"],
            "stall_reason": diagnosis["stall_reason"],
            "confidence": diagnosis["confidence"],
            "reasoning": diagnosis["reasoning"],
            "recommended_action": recommendation["recommended_action"],
            "urgency": recommendation["urgency"],
        })

    return created


def decide_approval(approval_id: int, approved: bool) -> dict:
    """Records a human's decision on a pending approval."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE approvals
                SET status = %s, reviewed_by = %s, reviewed_at = NOW()
                WHERE approval_id = %s
                RETURNING approval_id, deal_id, proposed_action, status
            """, ("approved" if approved else "rejected", "api_reviewer", approval_id))
            result = cur.fetchone()

            if result is None:
                conn.commit()
                return None

            cur.execute("""
                INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
                VALUES (%s, 'Orchestrator', %s, %s, NOW())
            """, (
                result["deal_id"],
                "action_approved" if approved else "action_rejected",
                result["proposed_action"],
            ))
        conn.commit()

    return dict(result)
