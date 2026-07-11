# Architecture

## High-Level Design

```text
Next.js Frontend  <----HTTP/JSON---->  FastAPI Backend  <----HTTP---->  CelesTrak
                                            |
                                            +---- SQLite (satellites + conjunctions)
                                            |
                                            +---- OpenRouter (optional AI analysis)
```

## Backend Flow

1. **Fetch**: Download TLEs from configured CelesTrak groups in parallel.
2. **Normalize**: Parse, deduplicate by NORAD ID, and upsert into SQLite.
3. **Propagate**: Use SGP4 to compute orbital states.
4. **Detect**: Find close approaches (KD-tree path for larger datasets).
5. **Classify**: Label risk using distance thresholds:
   - HIGH: `< 10 km`
   - MEDIUM: `< 50 km`
   - LOW: `< 200 km`
6. **Analyze (optional)**: AI-based recommendations and summaries through OpenRouter.

## Core Backend Modules

- `backend/main.py`: FastAPI app, endpoints, scheduler, caching.
- `backend/fetcher.py`: TLE ingestion and storage.
- `backend/propagator.py`: Position/orbit propagation.
- `backend/detector.py`: Conjunction detection pipeline.
- `backend/ai_service.py`: AI integration and response caching.
- `backend/db.py`: SQLite initialization, migrations, and access.

## Frontend Responsibilities

- Poll backend status and data endpoints.
- Render 3D globe and satellite layers.
- Display conjunction/proximity/risk information.
- Trigger manual fetch/detect actions.

## Caching Strategy

- Position cache for `/positions/all`
- Proximity cache for `/proximity`
- AI response cache inside `ai_service.py`

Caching reduces repeated SGP4 and AI request overhead for frequent UI refreshes.
