# SpaceTrackOps

Real-time satellite situational awareness platform — tracks ~17,000 satellites, detects close-approach events (conjunctions), and provides AI-powered risk analysis.

## Architecture

```
┌──────────────────┐     HTTP/JSON     ┌──────────────────────────────┐
│  Next.js 16      │ ◄──────────────── │  FastAPI Backend              │
│  React 19        │                   │                              │
│  3D Globe        │                   │  SGP4 Propagation            │
│  (react-globe.gl)│                   │  KD-Tree Conjunction Detect  │
│  Tailwind CSS 4  │                   │  OpenRouter AI Analysis      │
└──────────────────┘                   │  SQLite (spacetrackops.db)   │
                                       └──────────┬───────────────────┘
                                                  │
                                       ┌──────────▼───────────────────┐
                                       │  CelesTrak (TLE Data Source) │
                                       └──────────────────────────────┘
```

### Data Pipeline

1. **Fetch** — Parallel download of TLE data from 9 CelesTrak groups (~17K satellites)
2. **Store** — Dedup by NORAD ID, upsert into SQLite
3. **Propagate** — SGP4 orbit propagation for all satellites (8 parallel workers)
4. **Detect** — KD-tree pairwise search finds close approaches within 200 km threshold
5. **Classify** — Risk levels: HIGH (<10 km), MEDIUM (<50 km), LOW (<200 km)
6. **Analyze** — Optional AI risk summaries via OpenRouter API

## Prerequisites

- **Python 3.11+** with pip
- **Node.js 18+** with npm

## Quick Start

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn[standard] sgp4 numpy scipy requests apscheduler python-dotenv

# Configure (optional — AI features require an API key)
cp .env.example .env
# Edit .env with your OpenRouter API key

# Start the server
uvicorn main:app --reload
```

The backend runs at `http://127.0.0.1:8000`. On first startup, it automatically fetches satellite data from CelesTrak.

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure API endpoint (optional, defaults to http://127.0.0.1:8000)
cp .env.example .env.local

# Start development server
npm run dev
```

Open `http://localhost:3000` to view the dashboard.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/status` | System stats (satellite/conjunction counts, scheduler) |
| `POST` | `/fetch` | Trigger TLE fetch from CelesTrak |
| `GET` | `/satellites/categories` | Category list with counts |
| `GET` | `/satellites` | Paginated satellite list (`?search=&limit=&offset=&category=`) |
| `GET` | `/satellites/{norad_id}` | Single satellite detail |
| `GET` | `/position/{norad_id}` | Current position via SGP4 |
| `GET` | `/orbit/{norad_id}` | Orbit track (`?hours=&step=`) |
| `GET` | `/positions/all` | Batch positions for all satellites |
| `POST` | `/detect` | Run conjunction detection (`?hours=&step=&threshold=`) |
| `GET` | `/conjunctions` | Stored conjunction events (`?risk=&limit=`) |
| `GET` | `/proximity` | Closest satellite pairs (real-time KD-tree) |
| `POST` | `/ai/analyze-conjunction` | AI analysis of a conjunction |
| `GET` | `/ai/summary` | AI summary of top risks |

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | For AI features | — | OpenRouter API key |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | No | `http://127.0.0.1:8000` | Backend API URL |

## License

Private — all rights reserved.
