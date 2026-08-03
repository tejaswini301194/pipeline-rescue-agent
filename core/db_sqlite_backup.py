import sqlite3
from pathlib import Path

DB_PATH = Path("data/crm.db")

def get_connection():
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates tables if they don't exist yet. Safe to call every run."""
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS deals (
        deal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT NOT NULL,
        deal_value REAL NOT NULL,
        stage TEXT NOT NULL,
        owner TEXT NOT NULL,
        last_contacted_date TEXT,
        expected_close_date TEXT,
        created_date TEXT NOT NULL,
        status TEXT DEFAULT 'open'
    );

    CREATE TABLE IF NOT EXISTS activity_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        deal_id INTEGER NOT NULL,
        agent_name TEXT NOT NULL,
        action TEXT NOT NULL,
        detail TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (deal_id) REFERENCES deals(deal_id)
    );

    CREATE TABLE IF NOT EXISTS approvals (
        approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
        deal_id INTEGER NOT NULL,
        proposed_action TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        reviewed_by TEXT,
        reviewed_at TEXT
    );
    """)
    conn.commit()
    conn.close()

def seed_sample_deals():
    """Adds a few fake stuck/healthy deals so you have data to test with."""
    conn = get_connection()
    sample = [
        ("Acme Corp", 52000, "Negotiation", "Tejaswini", "2026-06-10", "2026-07-01", "2026-05-01"),
        ("Beta Industries", 18000, "Prospecting", "Tejaswini", "2026-07-25", "2026-08-15", "2026-07-01"),
        ("Globex LLC", 91000, "Proposal", "Tejaswini", "2026-06-01", "2026-06-20", "2026-04-15"),
    ]
    conn.executemany("""
        INSERT INTO deals (account_name, deal_value, stage, owner,
                            last_contacted_date, expected_close_date, created_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, sample)
    conn.commit()
    conn.close()
