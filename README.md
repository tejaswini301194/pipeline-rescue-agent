# Pipeline Rescue Agent

A multi-agent AI system that scans a sales CRM pipeline, diagnoses why deals have stalled, recommends a rescue action, and requires human approval before anything gets acted on.

Built as a portfolio project to explore multi-agent orchestration, tool-calling via MCP, and human-in-the-loop safety design — then extended into a production-style deployment (Postgres, FastAPI, Docker).

## What it does

Given a table of sales deals, the system:

1. **Scans** for deals that haven't been contacted recently (configurable threshold)
2. **Diagnoses** why each one has likely stalled (e.g. no follow-up, price objection, stage stuck too long, past-due close date) using an LLM reasoning over structured deal data and activity history
3. **Recommends** one concrete next action for a human sales rep to take
4. **Stops and waits for human approval** before anything is considered "actioned" — no email gets sent, no CRM record gets changed, without an explicit yes from a person
5. **Logs everything** — every diagnosis, every recommendation, every approval or rejection, with timestamps

The core design principle: **agents can suggest, only a human can approve.**

## Architecture

Orchestrator
|
|--> Diagnostic Agent --> Claude API (guided by skills/diagnose_stall.SKILL.md)
|--> Recommendation Agent --> Claude API (guided by skills/recommend_action.SKILL.md)
|--> Human Approval Gate --> blocks until a decision is made
|
`--> Postgres (deals, activity_log, approvals)


Two ways to run the pipeline:

- **CLI (`main.py`)** — scans, diagnoses, and pauses at a terminal prompt for `y`/`n` on each stalled deal. Good for local testing and demos.
- **API (`app.py`)** — `POST /scan` runs diagnosis + recommendation for all stalled deals and returns immediately (non-blocking). A human reviews `GET /approvals/pending` and decides later via `POST /approvals/{id}/decide`. This is the pattern a real unattended deployment would use — nothing waits on someone sitting at a keyboard.

Tool access for agents is designed around **MCP (Model Context Protocol)** (`mcp_server/crm_server.py`) — the intended architecture is for agents to call named tools (`get_stalled_deals`, `log_action`, `request_approval`) rather than write raw SQL directly.

## Tech stack

| Tool | Role |
|---|---|
| Python 3.11+ | Core language |
| Anthropic Claude API | Diagnosis and recommendation reasoning |
| MCP (Model Context Protocol) | Standardized tool-calling layer for agent-to-database access |
| PostgreSQL (Dockerized) | Persistent storage — deals, activity log, approvals |
| FastAPI + Uvicorn | Non-blocking HTTP API for unattended/scheduled operation |
| Agent Skills (`SKILL.md` files) | Versioned, plain-language instructions that define each agent's role and rules, loaded as system prompts |
| psycopg + SQLAlchemy | Postgres connectivity |
| python-dotenv | Environment/secret management |
| rich | Terminal UI for the CLI approval prompt |

## Project structure

pipeline-rescue-agent/
├── agents/
│ ├── orchestrator.py # CLI pipeline (blocking approval)
│ ├── orchestrator_api.py # API pipeline (non-blocking, decide-later)
│ ├── diagnostic_agent.py
│ └── recommendation_agent.py
├── core/
│ ├── db.py # Postgres connection + schema
│ ├── approval_gate.py # CLI human-in-the-loop prompt
│ └── mcp_client.py # MCP client wrapper
├── mcp_server/
│ └── crm_server.py # MCP tool server (get_stalled_deals, log_action, etc.)
├── skills/
│ ├── diagnose_stall.SKILL.md
│ └── recommend_action.SKILL.md
├── app.py # FastAPI application
├── main.py # CLI entry point
└── requirements.txt


## Setup

```bash
# Clone and enter the project
git clone https://github.com/tejaswini301194/pipeline-rescue-agent.git
cd pipeline-rescue-agent

# Create and activate a virtual environment
python -m venv venv
source venv/Scripts/activate      # Windows Git Bash
# source venv/bin/activate        # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root:

ANTHROPIC_API_KEY=your-key-here
DATABASE_URL=postgresql://pipeline_user:localdevpassword@localhost:5432/pipeline_rescue


Start Postgres via Docker:

```bash
docker run --name pipeline-rescue-db \
  -e POSTGRES_USER=pipeline_user \
  -e POSTGRES_PASSWORD=localdevpassword \
  -e POSTGRES_DB=pipeline_rescue \
  -p 5432:5432 \
  -d postgres:16
```

## Running it

**CLI version:**

```bash
python main.py
```

Scans for stalled deals, diagnoses each one, and prompts `y`/`n` before recording a decision.

**API version:**

```bash
uvicorn app:app --reload --port 8000
```

Then, from another terminal:

```bash
# Scan for stalled deals (runs diagnosis + recommendation, returns immediately)
curl -X POST "http://localhost:8000/scan?days_since_contact=14"

# See what's waiting on a decision
curl http://localhost:8000/approvals/pending

# Approve or reject a specific one
curl -X POST http://localhost:8000/approvals/{approval_id}/decide \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

## Reliability notes

A few real issues were found and fixed during development, worth documenting rather than hiding:

- **Category ambiguity**: when a deal matched more than one stall category (e.g. both "no follow-up" and "past-due close date"), the model's choice was inconsistent across runs. Fixed by adding an explicit priority order to the diagnosis skill file.
- **Temporal grounding**: the model had no reliable notion of "today's date" and sometimes misjudged whether a close date had already passed. Fixed by explicitly passing the current date into every diagnosis prompt.
- **JSON contract drift**: the model occasionally wrapped its JSON output in markdown code fences despite instructions not to. Fixed with a stripping step before parsing, rather than relying on prompt instructions alone.

## Known limitations / what's next

- **API key authentication is in place** for all data-modifying and data-reading endpoints (`/health` intentionally remains open for uptime checks). Not yet OAuth/multi-user — a single shared key, appropriate for this project's current scope.
- **MCP tools are defined but not yet the primary data-access path** — the orchestrator currently talks to Postgres directly for speed; wiring agents through the MCP client (`core/mcp_client.py`) as the actual data layer is the next architectural step.
- **Local Postgres only** — not yet pointed at a hosted database.
- **Not yet containerized or cloud-deployed** — Docker packaging of the FastAPI app and AWS deployment are planned next steps.
- **No automated eval suite yet** — `eval/quick_eval.py` exists as a starting point but needs a larger hand-labeled test set for a real accuracy benchmark.

## Roadmap

- [ ] Docker containerization of the FastAPI app
- [ ] Deploy to AWS
- [ ] Add authentication to API endpoints
- [ ] Wire agents through MCP as the primary tool-calling layer
- [ ] Add LangSmith or Braintrust tracing for observability
- [ ] Expand eval suite and publish a reliability report

## Live deployment

This project has been deployed to AWS as a real, working demonstration:

- **Compute**: Docker container running on an EC2 instance (Ubuntu 22.04)
- **Database**: Amazon RDS (PostgreSQL), publicly accessible with a dedicated security group
- **Container registry**: Amazon ECR, storing the built image
- **API authentication**: enforced via `X-API-Key` header on all data-modifying/reading endpoints

**Note:** the live instance is stopped between demos to avoid ongoing cloud costs. To resume it and get a current public URL, restart the EC2 instance and RDS database via the AWS CLI or console, then retrieve the instance's public IP — the container and database contents persist across stop/start cycles.

Deployment was done manually via AWS CLI (ECR push, EC2 provisioning, RDS setup, Docker run with environment-injected secrets) rather than an automated pipeline — a natural next step would be Infrastructure as Code (Terraform or CloudFormation) and a CI/CD pipeline for repeatable deployments.
