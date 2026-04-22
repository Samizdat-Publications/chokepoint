# ChokePoint

**Open intelligence platform: Strait of Hormuz tanker traffic vs. global oil prices.**

ChokePoint monitors real-time tanker traffic through the Strait of Hormuz, correlates it with Brent crude futures and landed consumer costs, and surfaces financial anomalies that precede major geopolitical announcements.

## Repository Structure

```
chokepoint/
├── db/schema/          SQL migrations for TimescaleDB
├── pipelines/          Python data ingestion pipelines
│   ├── common/         Shared DB and config helpers
│   ├── vessel_positions/   AIS vessel tracking pipeline
│   ├── oil_prices/     EIA/FRED/Alpha Vantage price pipeline
│   ├── cot_reports/    CFTC Commitments of Traders pipeline
│   └── events/         GDELT geopolitical events pipeline
└── .github/workflows/  CI/CD
```

## Quick Start

### Database

```bash
psql $DATABASE_URL -f db/schema/001_enable_timescaledb.sql
psql $DATABASE_URL -f db/schema/002_vessel_positions.sql
# ... run remaining migrations in order
```

### AIS Pipeline

```bash
cd pipelines
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Stream AIS positions via aisstream.io (free API key at https://aisstream.io)
AISSTREAM_API_KEY=your_key DATABASE_URL=postgresql://... python -m vessel_positions

# Or poll MarineTraffic REST API (commercial key required)
AIS_SOURCE=marinetraffic MARINETRAFFIC_API_KEY=your_key DATABASE_URL=postgresql://... python -m vessel_positions
```

## Environment Variables

See `.env.example` for full list.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL + TimescaleDB connection string |
| `AISSTREAM_API_KEY` | MVP | aisstream.io free API key |
| `MARINETRAFFIC_API_KEY` | Alt | MarineTraffic commercial API key |
| `SPIRE_API_TOKEN` | Alt | Spire Maritime API token |

## Data Sources

- **AIS Vessel Tracking:** [aisstream.io](https://aisstream.io) (free) → MarineTraffic/Spire (commercial upgrade)
- **Oil Prices:** EIA API, FRED API, Alpha Vantage
- **COT Reports:** CFTC (free weekly CSV)
- **Geopolitical Events:** GDELT Project

## Architecture

See [CHOKEPOINT-BRIEF.md](https://github.com/Samizdat-Publications/chokepoint/blob/main/CHOKEPOINT-BRIEF.md) for full platform architecture and roadmap.
