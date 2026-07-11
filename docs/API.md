# API Reference

Base URL (local): `http://127.0.0.1:8000`

## Health & Status

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Basic health response with version |
| GET | `/status` | Satellite/conjunction counts, scheduler state, and run metadata |

## Data Ingestion

| Method | Endpoint | Description |
|---|---|---|
| POST | `/fetch` | Fetch latest TLE data and upsert satellites |

## Satellites

| Method | Endpoint | Description |
|---|---|---|
| GET | `/satellites/categories` | Category list with counts |
| GET | `/satellites` | Paginated list with optional `search`, `category`, `limit`, `offset` |
| GET | `/satellites/{norad_id}` | Satellite details including TLE lines |

## Propagation & Positions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/position/{norad_id}` | Current propagated state |
| GET | `/orbit/{norad_id}` | Orbit track (`hours`, `step`) |
| GET | `/positions/all` | Batch current positions (optional `category`) |

## Conjunctions & Proximity

| Method | Endpoint | Description |
|---|---|---|
| POST | `/detect` | Run conjunction detection (`hours`, `step`, `threshold`) |
| GET | `/conjunctions` | Stored conjunction events (`risk`, `limit`) |
| GET | `/proximity` | Current nearest pairs (`limit`) |

## AI Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ai/analyze-conjunction` | Analyze one conjunction payload |
| GET | `/ai/summary` | AI summaries for top-risk conjunctions (`limit`) |

## Notes

- AI endpoints require `OPENROUTER_API_KEY`.
- `/positions/all` and `/proximity` responses are cached server-side.
