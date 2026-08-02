from dotenv import load_dotenv
load_dotenv()

from core.db import init_db, seed_sample_deals
from agents.orchestrator import run_pipeline

if __name__ == "__main__":
    init_db()
    # Run seed_sample_deals() once to populate test data, then comment it out
    # seed_sample_deals()
    run_pipeline(days_since_contact=14)
