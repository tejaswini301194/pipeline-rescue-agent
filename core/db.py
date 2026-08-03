from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]

@contextmanager
def get_connection():
    """Yields a psycopg connection configured to return rows as dicts,
    mirroring how sqlite3.Row worked before."""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Creates tables if they don't exist yet. Safe to call every run."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id SERIAL PRIMARY KEY,
                account_name TEXT NOT NULL,
                deal_value REAL NOT NULL,
                stage TEXT NOT NULL,
                owner TEXT NOT NULL,
                last_contacted_date DATE,
                expected_close_date DATE,
                created_date DATE NOT NULL,
                status TEXT DEFAULT 'open'
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                log_id SERIAL PRIMARY KEY,
                deal_id INTEGER NOT NULL REFERENCES deals(deal_id),
                agent_name TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT,
                timestamp TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS approvals (
                approval_id SERIAL PRIMARY KEY,
                deal_id INTEGER NOT NULL REFERENCES deals(deal_id),
                proposed_action TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewed_by TEXT,
                reviewed_at TIMESTAMP
            );
            """)
        conn.commit()

def seed_sample_deals():
    """Adds a few fake stuck/healthy deals so you have data to test with."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            sample = [
                ("Acme Corp", 52000, "Negotiation", "Tejaswini", "2026-06-10", "2026-07-01", "2026-05-01"),
                ("Beta Industries", 18000, "Prospecting", "Tejaswini", "2026-07-25", "2026-08-15", "2026-07-01"),
                ("Globex LLC", 91000, "Proposal", "Tejaswini", "2026-06-01", "2026-06-20", "2026-04-15"),
            ]
            cur.executemany("""
                INSERT INTO deals (account_name, deal_value, stage, owner,
                                    last_contacted_date, expected_close_date, created_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, sample)
        conn.commit()
