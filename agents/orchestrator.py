from core.db import init_db, get_connection
from agents.diagnostic_agent import diagnose
from agents.recommendation_agent import recommend
from core.approval_gate import request_human_approval

def run_pipeline(days_since_contact: int = 14):
    init_db()
    conn = get_connection()

    stalled = conn.execute("""
        SELECT * FROM deals
        WHERE status = 'open'
        AND julianday('now') - julianday(last_contacted_date) >= ?
    """, (days_since_contact,)).fetchall()

    print(f"Found {len(stalled)} stalled deal(s).")

    for row in stalled:
        deal = dict(row)

        history = conn.execute(
            "SELECT * FROM activity_log WHERE deal_id = ?", (deal["deal_id"],)
        ).fetchall()
        history = [dict(h) for h in history]

        # Step A: diagnose
        diagnosis = diagnose(deal, history)
        conn.execute("""
            INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
            VALUES (?, 'DiagnosticAgent', 'diagnosed', ?, datetime('now'))
        """, (deal["deal_id"], diagnosis["stall_reason"]))
        conn.commit()

        # Step B: recommend
        recommendation = recommend(diagnosis)

        # Step C: STOP and ask the human -- nothing auto-executes
        approved = request_human_approval(deal, diagnosis, recommendation)

        if approved:
            conn.execute("""
                INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
                VALUES (?, 'Orchestrator', 'action_approved', ?, datetime('now'))
            """, (deal["deal_id"], recommendation["recommended_action"]))
        else:
            conn.execute("""
                INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
                VALUES (?, 'Orchestrator', 'action_rejected', ?, datetime('now'))
            """, (deal["deal_id"], recommendation["recommended_action"]))
        conn.commit()

    conn.close()
    print("Pipeline run complete.")
