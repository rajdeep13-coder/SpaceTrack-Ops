# SpaceTrackOps

SpaceTrackOps is a real-time satellite situational awareness platform that:
- ingests CelesTrak TLE feeds,
- propagates orbital positions with SGP4,
- detects close approaches (conjunctions),
- and provides optional AI-assisted risk insights.

## 🏆 Recognition
SpaceTrack-Ops was featured by the [**IIMCIP TIC**](https://www.linkedin.com/company/iimcip-tic/) on their official LinkedIn channel for its approach to identifying close-approach satellite events. 
[Check out the feature here](https://www.linkedin.com/posts/buildclub-studentprojects-ugcPost-7483758081714216960-oN8D/?utm_source=social_share_send&utm_medium=member_desktop_web&rcm=ACoAAE7VVA8BiXaZ5RDr0NHwoEiHHa9e4BaejXM).

## Requirements

- Python 3.11+
- Node.js 18+
- npm

## Repository Structure

```text
SpaceTrack-Ops/
├── backend/     # FastAPI backend, ingestion, propagation, detection, AI layer
├── frontend/    # Next.js dashboard with 3D globe UI
├── docs/        # Detailed project documentation
└── .env.example # Shared environment variable template
```

## Quick Start

### 1) Configure environment

From repository root:

```bash
cp .env.example .env
```

Update `.env` values as needed (especially `OPENROUTER_API_KEY` for AI endpoints).

### 2) Run backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install fastapi "uvicorn[standard]" sgp4 numpy scipy requests apscheduler python-dotenv
uvicorn main:app --reload
```

Backend: `http://127.0.0.1:8000`

### 3) Run frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

If needed, create `frontend/.env.local` manually with:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Key Features

- Parallel TLE ingestion from multiple CelesTrak groups
- SQLite-backed satellite and conjunction storage
- KD-tree optimized conjunction detection
- Cached batch position and proximity APIs
- Optional AI analysis and summaries via OpenRouter

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/status` | Service and scheduler status |
| POST | `/fetch` | Fetch/refresh satellite TLE data |
| GET | `/satellites` | Paginated satellite list with filters |
| GET | `/positions/all` | Current positions (cached) |
| POST | `/detect` | Run conjunction detection |
| GET | `/conjunctions` | Retrieve stored conjunction events |
| GET | `/proximity` | Nearest current satellite pairs |
| POST | `/ai/analyze-conjunction` | AI analysis for a single event |
| GET | `/ai/summary` | AI summary for top events |

For the full reference, see:
- `/home/runner/work/SpaceTrack-Ops/SpaceTrack-Ops/docs/API.md`
- `/home/runner/work/SpaceTrack-Ops/SpaceTrack-Ops/docs/ARCHITECTURE.md`
- `/home/runner/work/SpaceTrack-Ops/SpaceTrack-Ops/docs/SETUP.md`

## License

Private repository — all rights reserved.
