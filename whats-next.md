<original_task>
HOR-2: Set up repo, CI/CD, database schema, and project scaffolding for the ChokePoint platform.

Specific requirements from issue description:
1. Initialize a Next.js 15 (app router) project with TypeScript and Tailwind CSS
2. Set up PostgreSQL + TimescaleDB schema for: vessel_positions, oil_prices, events, cot_reports
3. Set up a Python data pipeline directory (pipelines/) with dependency management
4. Configure GitHub Actions CI (lint, type-check, build)
5. Deploy initial skeleton to Vercel

Reference doc: CHOKEPOINT-BRIEF.md (exists at /workspaces/14f87d75-6889-4423-9dcb-b185889c40d5/CHOKEPOINT-BRIEF.md)
</original_task>

<work_completed>
Nothing has been implemented yet. This is the first heartbeat on this issue.

Research completed this session:
- Read CHOKEPOINT-BRIEF.md (CEO's architecture doc from HOR-1)
- Confirmed full tech stack, schema requirements, and deployment targets
- Confirmed Paperclip API auth pattern (PAPERCLIP_API_KEY env var, http://127.0.0.1:3100)
- Confirmed issue HOR-2 is checked out to this agent (run ID: 47a15ba5-8565-4c79-9f69-bea7083ef27d)
- Confirmed workspace is empty (C:\Users\stewa\.paperclip\instances\default\workspaces\bcc3904f-fffb-4043-aa1a-40ebbc8c7853)
- Confirmed no GitHub repo exists yet (needs to be created)
- Confirmed no Vercel project exists yet
</work_completed>

<work_remaining>
All work is remaining. Ordered by dependency:

## Step 1: Create GitHub Repository
- Create a new GitHub repo: `chokepoint` (or `chokepoint-platform`)
- Use GitHub CLI: `gh repo create chokepoint --public --description "Intelligence platform: Strait of Hormuz shipping traffic vs oil prices"`
- Initialize with README, .gitignore (Node + Python), MIT license

## Step 2: Initialize Next.js Project
Run in workspace root:
```bash
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```
- Next.js 15 with App Router
- TypeScript
- Tailwind CSS
- ESLint

## Step 3: Add Project Dependencies
```bash
npm install @mapbox/mapbox-gl-js recharts d3 @types/d3
npm install -D prettier
```

## Step 4: Create Database Schema Files
Create `db/schema/` with these migration SQL files:
- `001_enable_timescaledb.sql` — `CREATE EXTENSION IF NOT EXISTS timescaledb;`
- `002_vessel_positions.sql` — vessel_positions table + hypertable
- `003_oil_prices.sql` — oil_prices table + hypertable  
- `004_events.sql` — events table (geopolitical events)
- `005_cot_reports.sql` — cot_reports table (CFTC Commitments of Traders)

See Schema Details section below for exact column specs.

## Step 5: Set Up Python Pipelines Directory
```
pipelines/
  requirements.txt          (aiohttp, psycopg2-binary, pandas, requests, python-dotenv)
  requirements-dev.txt      (pytest, ruff, mypy)
  pyproject.toml            (ruff config, mypy config)
  README.md
  __init__.py
  common/
    __init__.py
    db.py                   (PostgreSQL connection helper)
    config.py               (env var loading)
  vessel_positions/
    __init__.py
    marinetraffic.py        (stub AIS ingestion)
  oil_prices/
    __init__.py
    eia.py                  (stub EIA ingestion)
    fred.py                 (stub FRED ingestion)
  cot_reports/
    __init__.py
    cftc.py                 (stub COT ingestion)
  events/
    __init__.py
    gdelt.py                (stub GDELT ingestion)
```

## Step 6: Configure GitHub Actions CI
Create `.github/workflows/ci.yml`:
- Trigger: push + PR on main
- Jobs: lint (ESLint + Prettier check), type-check (tsc --noEmit), build (next build)
- Optional: Python ruff lint job for pipelines/

## Step 7: Create Skeleton Next.js Pages
- `src/app/page.tsx` — Homepage with placeholder "ChokePoint" heading
- `src/app/layout.tsx` — Root layout with Tailwind base
- `src/app/map/page.tsx` — Placeholder vessel map page
- `src/app/prices/page.tsx` — Placeholder price chart page
- Basic Tailwind config with dark mode and custom colors

## Step 8: Environment Configuration
- `.env.example` with required vars: DATABASE_URL, REDIS_URL, MARINETRAFFIC_API_KEY, EIA_API_KEY, etc.
- `.env.local` (gitignored) for local dev
- `src/lib/env.ts` — typed env validation (use zod or t3-env)

## Step 9: Deploy to Vercel
- `vercel.json` (or zero-config)
- Push to GitHub
- Connect Vercel to GitHub repo via `vercel` CLI or dashboard
- Set environment variables in Vercel

## Step 10: Post-work
- Comment on HOR-2 in Paperclip with what was done
- Update issue status to `in_review` or `done`
- Use: `curl -X POST http://127.0.0.1:3100/api/issues/ff6cb114-2fc8-4e20-be28-3d42f67a4ed8/comment -H "Authorization: Bearer $PAPERCLIP_API_KEY" -H "Content-Type: application/json" -d '{"body":"..."}'`
- Use: `curl -X PATCH http://127.0.0.1:3100/api/issues/ff6cb114-2fc8-4e20-be28-3d42f67a4ed8 -H "Authorization: Bearer $PAPERCLIP_API_KEY" -H "Content-Type: application/json" -d '{"status":"done"}'`

**Always include header: `X-Paperclip-Run-Id: 47a15ba5-8565-4c79-9f69-bea7083ef27d` on mutating API calls.**
</work_remaining>

<attempted_approaches>
- Tried to load ecc-resume-session skill — no session file found (fresh start)
- Tried to load claude-api skill — loaded but not relevant to this task
- Searched for Paperclip skill in ~/.claude/skills/ — none exists (Paperclip interaction must be done via direct API calls)
- Attempted auth via JWT secret directly — failed; correct auth is via PAPERCLIP_API_KEY env var
</attempted_approaches>

<critical_context>
## Paperclip API
- Base URL: http://127.0.0.1:3100
- Auth: `Authorization: Bearer $PAPERCLIP_API_KEY` (env var already set in process)
- Run ID for X-Paperclip-Run-Id header: `47a15ba5-8565-4c79-9f69-bea7083ef27d`
- Issue ID: `ff6cb114-2fc8-4e20-be28-3d42f67a4ed8`
- Company ID: `30303548-3beb-45ac-a484-e568fe73683e`
- Agent ID: `bcc3904f-fffb-4043-aa1a-40ebbc8c7853` (CTO)
- Issue is checked out to this agent — do NOT call checkout again

## Project: ChokePoint
- Intelligence platform: Strait of Hormuz tanker traffic vs. oil price correlation
- Goal: make energy market manipulation legible to ordinary people
- Full brief: `/workspaces/14f87d75-6889-4423-9dcb-b185889c40d5/CHOKEPOINT-BRIEF.md`

## Tech Stack (from CHOKEPOINT-BRIEF.md)
- Frontend: Next.js 15 (React 19), App Router, TypeScript, Tailwind CSS, Mapbox GL JS, D3.js + Recharts
- Backend: Node.js (Hono or Express REST API), Python pipelines
- Database: PostgreSQL + TimescaleDB (time-series extension)
- Cache: Redis
- Hosting: Vercel (frontend), Railway or Fly.io (backend services)
- CI/CD: GitHub Actions

## Database Schema Details
All four tables need TimescaleDB hypertables (time-series partitioning by `time` column):

### vessel_positions
```sql
CREATE TABLE vessel_positions (
  time        TIMESTAMPTZ NOT NULL,
  mmsi        BIGINT NOT NULL,           -- Maritime Mobile Service Identity
  vessel_name TEXT,
  vessel_type TEXT,
  lat         DOUBLE PRECISION NOT NULL,
  lon         DOUBLE PRECISION NOT NULL,
  speed       REAL,                      -- knots
  course      REAL,                      -- degrees
  destination TEXT,
  source      TEXT NOT NULL DEFAULT 'marinetraffic'
);
SELECT create_hypertable('vessel_positions', 'time');
CREATE INDEX ON vessel_positions (mmsi, time DESC);
```

### oil_prices
```sql
CREATE TABLE oil_prices (
  time        TIMESTAMPTZ NOT NULL,
  series_id   TEXT NOT NULL,             -- e.g. 'BRENT_SPOT', 'WTI_FUTURES', 'RETAIL_GASOLINE_US'
  source      TEXT NOT NULL,             -- 'eia', 'fred', 'alpha_vantage'
  price       DOUBLE PRECISION NOT NULL,
  currency    TEXT NOT NULL DEFAULT 'USD',
  unit        TEXT NOT NULL              -- 'barrel', 'gallon', 'mmbtu'
);
SELECT create_hypertable('oil_prices', 'time');
CREATE INDEX ON oil_prices (series_id, time DESC);
```

### events
```sql
CREATE TABLE events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  time        TIMESTAMPTZ NOT NULL,
  title       TEXT NOT NULL,
  description TEXT,
  event_type  TEXT NOT NULL,             -- 'geopolitical', 'sanctions', 'attack', 'weather'
  location    TEXT,
  lat         DOUBLE PRECISION,
  lon         DOUBLE PRECISION,
  source      TEXT NOT NULL,             -- 'gdelt', 'newsapi', 'manual'
  source_id   TEXT,
  severity    INTEGER CHECK (severity BETWEEN 1 AND 5),
  tags        TEXT[] DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON events (time DESC);
CREATE INDEX ON events (event_type, time DESC);
```

### cot_reports
```sql
CREATE TABLE cot_reports (
  time                    TIMESTAMPTZ NOT NULL,
  commodity               TEXT NOT NULL,         -- 'CRUDE_OIL_WTI', 'BRENT_CRUDE'
  report_date             DATE NOT NULL,
  commercial_long         BIGINT,
  commercial_short        BIGINT,
  noncommercial_long      BIGINT,
  noncommercial_short     BIGINT,
  noncommercial_spreads   BIGINT,
  open_interest           BIGINT,
  source                  TEXT NOT NULL DEFAULT 'cftc'
);
SELECT create_hypertable('cot_reports', 'time');
CREATE INDEX ON cot_reports (commodity, time DESC);
```

## Workspace Location
- My workspace (where all code goes): `C:\Users\stewa\.paperclip\instances\default\workspaces\bcc3904f-fffb-4043-aa1a-40ebbc8c7853`
- CEO workspace (reference only): `C:\Users\stewa\.paperclip\instances\default\workspaces\14f87d75-6889-4423-9dcb-b185889c40d5`

## GitHub
- Need to create a new repo — none exists yet
- Use `gh` CLI (available in PATH) with `gh repo create`
- Check for existing GitHub auth: `gh auth status`

## Vercel
- Need to connect after repo is created
- Use `vercel` CLI or dashboard
- Check if Vercel CLI is installed: `vercel --version`

## Assumptions to Validate
1. GitHub CLI is authenticated (`gh auth status`)
2. Vercel CLI is available or can be installed (`npm i -g vercel`)
3. Node.js and npm are available (likely yes, since npm is in PATH)
4. Python 3 is available (`python3 --version`)
5. No existing repo named `chokepoint` on the GitHub account
</critical_context>

<current_state>
- Issue HOR-2 status: in_progress (checked out to this agent)
- Workspace: completely empty
- Code written: none
- GitHub repo: does not exist
- Vercel project: does not exist
- Database: not set up (just schema SQL files needed for this task)

**This is a ground-zero start.** The next agent should:
1. First run `gh auth status` and `node --version` to verify tooling
2. Create the GitHub repo
3. Initialize Next.js in the workspace
4. Create db/schema/ SQL files
5. Create pipelines/ Python skeleton
6. Create .github/workflows/ci.yml
7. Push to GitHub
8. Deploy to Vercel
9. Comment on Paperclip issue and mark done

The work is entirely non-started. No partial state to recover from. Start fresh at Step 1.
</current_state>
