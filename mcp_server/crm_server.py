from mcp.server.fastmcp import FastMCP
from datetime import datetime
from core.db import get_connection

mcp = FastMCP("crm-pipeline")

@mcp.tool()
def get_stalled_deals(days_since_contact: int = 14) -> list[dict]:
    """
    Returns open deals that haven't been contacted in 'days_since_contact' days or more.
    This is the 'scan the hospital beds' tool.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM deals
                WHERE status = 'open'
                AND CURRENT_DATE - last_contacted_date >= %s
            """, (days_since_contact,))
            rows = cur.fetchall()
    return rows

@mcp.tool()
def get_deal_history(deal_id: int) -> list[dict]:
    """Returns every logged action taken on a specific deal so far."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM activity_log WHERE deal_id = %s ORDER BY timestamp", (deal_id,)
            )
            rows = cur.fetchall()
    return rows

@mcp.tool()
def log_action(deal_id: int, agent_name: str, action: str, detail: str = "") -> str:
    """Writes an entry to the activity log -- the 'diary' every agent must write in."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (deal_id, agent_name, action, detail, datetime.now()))
        conn.commit()
    return "logged"

@mcp.tool()
def request_approval(deal_id: int, proposed_action: str) -> int:
    """Creates a pending approval request. Returns the approval_id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO approvals (deal_id, proposed_action, status)
                VALUES (%s, %s, 'pending')
                RETURNING approval_id
            """, (deal_id, proposed_action))
            approval_id = cur.fetchone()["approval_id"]
        conn.commit()
    return approval_id

if __name__ == "__main__":
    mcp.run()
