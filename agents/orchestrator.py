from core.db import init_db, get_connection
from agents.diagnostic_agent import diagnose
from agents.recommendation_agent import recommend
from core.approval_gate import request_human_approval

def run_pipeline(days_since_contact: int = 14):
    init_db()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM deals
                WHERE status = 'open'
                AND CURRENT_DATE - last_contacted_date >= %s
            """, (days_since_contact,))
            stalled = cur.fetchall()

    print(f"Found {len(stalled)} stalled deal(s).")

    for deal in stalled:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM activity_log WHERE deal_id = %s", (deal["deal_id"],)
                )
                history = cur.fetchall()

        # Step A: diagnose
        diagnosis = diagnose(deal, history)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
                    VALUES (%s, 'DiagnosticAgent', 'diagnosed', %s, NOW())
                """, (deal["deal_id"], diagnosis["stall_reason"]))
            conn.commit()

        # Step B: recommend
        recommendation = recommend(diagnosis)

        # Step C: STOP and ask the human -- nothing auto-executes
        approved = request_human_approval(deal, diagnosis, recommendation)

        with get_connection() as conn:
            with conn.cursor() as cur:
                if approved:
                    cur.execute("""
                        INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
                        VALUES (%s, 'Orchestrator', 'action_approved', %s, NOW())
                    """, (deal["deal_id"], recommendation["recommended_action"]))
                else:
                    cur.execute("""
                        INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
                        VALUES (%s, 'Orchestrator', 'action_rejected', %s, NOW())
                    """, (deal["deal_id"], recommendation["recommended_action"]))
            conn.commit()

    print("Pipeline run complete.")
