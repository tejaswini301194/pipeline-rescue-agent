import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from core.db import init_db, get_connection
from agents.orchestrator_api import scan_and_propose, decide_approval

app = FastAPI(title="Pipeline Rescue Agent API")

API_KEY = os.environ["APP_API_KEY"]

def require_api_key(x_api_key: Optional[str] = Header(None)):
    """Every protected route depends on this. Rejects requests with a
    missing or incorrect X-API-Key header before any real work happens.
    Always returns 401 for any auth failure, whether the header is
    missing or simply wrong."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/scan", dependencies=[Depends(require_api_key)])
def scan(days_since_contact: int = 14):
    """Diagnoses and proposes actions for all stalled deals. Returns immediately, no blocking."""
    results = scan_and_propose(days_since_contact=days_since_contact)
    return {"scanned": len(results), "proposals": results}

@app.get("/approvals/pending", dependencies=[Depends(require_api_key)])
def list_pending():
    """Lists everything waiting on a human decision."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.approval_id, a.deal_id, d.account_name, d.deal_value,
                       a.proposed_action, a.status
                FROM approvals a
                JOIN deals d ON a.deal_id = d.deal_id
                WHERE a.status = 'pending'
                ORDER BY a.approval_id
            """)
            rows = cur.fetchall()
    return rows

class Decision(BaseModel):
    approved: bool

@app.post("/approvals/{approval_id}/decide", dependencies=[Depends(require_api_key)])
def decide(approval_id: int, decision: Decision):
    """A human approves or rejects a specific pending recommendation."""
    result = decide_approval(approval_id, decision.approved)
    if result is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return result
