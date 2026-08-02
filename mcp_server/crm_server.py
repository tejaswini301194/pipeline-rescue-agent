from mcp.server.fastmcp import FastMCP
from datetime import datetime, date
from core.db import get_connection

mcp = FastMCP("crm-pipeline")

@mcp.tool()
def get_stalled_deals(days_since_contact: int = 14) -> list[dict]:
    """
    Returns open deals that haven't been contacted in 'days_since_contact' days or more.
    This is the 'scan the hospital beds' tool.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM deals
        WHERE status = 'open'
        AND julianday('now') - julianday(last_contacted_date) >= ?
    """, (days_since_contact,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@mcp.tool()
def get_deal_history(deal_id: int) -> list[dict]:
    """Returns every logged action taken on a specific deal so far."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM activity_log WHERE deal_id = ? ORDER BY timestamp", (deal_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@mcp.tool()
def log_action(deal_id: int, agent_name: str, action: str, detail: str = "") -> str:
    """Writes an entry to the activity log -- the 'diary' every agent must write in."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO activity_log (deal_id, agent_name, action, detail, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (deal_id, agent_name, action, detail, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return "logged"

@mcp.tool()
def request_approval(deal_id: int, proposed_action: str) -> int:
    """Creates a pending approval request. Returns the approval_id."""
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO approvals (deal_id, proposed_action, status)
        VALUES (?, ?, 'pending')
    """, (deal_id, proposed_action))
    conn.commit()
    approval_id = cur.lastrowid
    conn.close()
    return approval_id

if __name__ == "__main__":
    mcp.run()
