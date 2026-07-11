"""
main.py — SpaceTrackOps FastAPI backend (Phase 8: proximity pairs for globe arc viz)

New in Phase 8:
  - GET /proximity returns the N closest satellite pairs right now
    (uses current SGP4 positions + scipy cKDTree for fast nearest-neighbour)
  - Risk thresholds updated: HIGH <10 km, MEDIUM <50 km, LOW <200 km
  - Default detect threshold raised to 200 km so real conjunctions are found
"""

import logging
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler

import numpy as np
from scipy.spatial import cKDTree

from db import get_conn, init_db
from fetcher import fetch_and_store
from propagator import get_position, get_orbit_track
from detector import run_detection
from ai_service import analyze_conjunction, summarize_top_risks
from utils import risk_label

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
AUTO_REFRESH_HOURS = 12
POSITIONS_CACHE_TTL_S = 15
PROXIMITY_CACHE_TTL_S = 60
MAX_WORKERS = 8
KNN_NEIGHBORS = 5

# ── Scheduler state ───────────────────────────────────────────────────────────
_state: dict = {
    "last_fetch_at":   None,
    "last_detect_at":  None,
    "runs_completed":  0,
    "is_running":      False,
    "lock":            threading.Lock(),
}

scheduler = BackgroundScheduler(daemon=True, timezone="UTC")

# ── Auto-refresh job ──────────────────────────────────────────────────────────

def _auto_refresh() -> None:
    """Fetch fresh TLEs from CelesTrak then re-run conjunction detection."""
    with _state["lock"]:
        if _state["is_running"]:
            logger.info("[scheduler] Already running, skipping.")
            return
        _state["is_running"] = True

    try:
        logger.info("[scheduler] Auto-refresh: fetching TLEs…")
        fetch_and_store()
        _state["last_fetch_at"] = datetime.now(timezone.utc).isoformat()

        logger.info("[scheduler] Auto-refresh: running detection…")
        run_detection()
        _state["last_detect_at"] = datetime.now(timezone.utc).isoformat()
        _state["runs_completed"] += 1
        logger.info(f"[scheduler] Auto-refresh complete (run #{_state['runs_completed']})")
    except Exception as e:
        logger.error(f"[scheduler] Auto-refresh failed: {e}")
    finally:
        _state["is_running"] = False


# ── Lifespan Context Manager ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()

    # Schedule recurring refresh
    scheduler.add_job(_auto_refresh, "interval", hours=AUTO_REFRESH_HOURS, id="auto_refresh")
    scheduler.start()

    # Bootstrap: if DB is empty, seed it in a background thread immediately
    with get_conn() as conn:
        sat_count = conn.execute("SELECT COUNT(*) FROM satellites").fetchone()[0]

    if sat_count == 0:
        logger.info("[startup] DB empty — triggering initial data load…")
        t = threading.Thread(target=_auto_refresh, daemon=True)
        t.start()
    else:
        logger.info(f"[startup] DB has {sat_count} satellites — ready.")
        
    yield
    
    # Shutdown
    scheduler.shutdown(wait=False)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="SpaceTrackOps Backend", version="2.0.0", lifespan=lifespan)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=(False if "*" in CORS_ORIGINS else True),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "SpaceTrackOps backend running", "version": "2.0.0"}


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/status")
def get_status():
    """
    Returns system health: satellite/conjunction counts, last run times,
    next scheduled refresh, and whether auto-refresh is currently executing.
    """
    with get_conn() as conn:
        sat_count  = conn.execute("SELECT COUNT(*) FROM satellites").fetchone()[0]
        conj_count = conn.execute("SELECT COUNT(*) FROM conjunctions").fetchone()[0]

    job      = scheduler.get_job("auto_refresh")
    next_run = None
    if job and job.next_run_time:
        next_run = job.next_run_time.isoformat()

    return {
        "satellites":         sat_count,
        "conjunctions":       conj_count,
        "last_fetch_at":      _state["last_fetch_at"],
        "last_detect_at":     _state["last_detect_at"],
        "runs_completed":     _state["runs_completed"],
        "auto_refresh_active": _state["is_running"],
        "scheduler_running":  scheduler.running,
        "next_scheduled":     next_run,
    }


# ── Data Ingestion ────────────────────────────────────────────────────────────

@app.post("/fetch")
def fetch_satellites():
    """Pull latest TLEs from CelesTrak and upsert into the DB."""
    try:
        result = fetch_and_store()
        _state["last_fetch_at"] = datetime.now(timezone.utc).isoformat()
        _invalidate_all_caches()
        return result
    except Exception as e:
        logger.error(f"Manual TLE fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Satellites ────────────────────────────────────────────────────────────────

@app.get("/satellites/categories")
def get_satellite_categories():
    """Returns a list of categories with satellite counts, ordered by count descending."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT COALESCE(category, 'unknown') AS name, COUNT(*) AS count
                 FROM satellites
                GROUP BY COALESCE(category, 'unknown')
                ORDER BY count DESC"""
        ).fetchall()
    return {"categories": [dict(r) for r in rows]}


@app.get("/satellites")
def get_satellites(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str = Query(default="", max_length=200),
    category: str = Query(default="", max_length=50)
):
    """Paginated satellite list with optional name search and category filter."""
    with get_conn() as conn:
        cursor = conn.cursor()
        filters: list[str] = []
        params:  list      = []

        if search:
            filters.append("name LIKE ?")
            params.append(f"%{search}%")
        if category:
            filters.append("category = ?")
            params.append(category)

        where = ("WHERE " + " AND ".join(filters)) if filters else ""

        rows = cursor.execute(
            f"SELECT norad_id, name, category, last_updated FROM satellites "
            f"{where} ORDER BY name LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        total = cursor.execute(
            f"SELECT COUNT(*) FROM satellites {where}", params
        ).fetchone()[0]

    return {"total": total, "satellites": [dict(r) for r in rows]}


@app.get("/satellites/{norad_id}")
def get_satellite(norad_id: str):
    """Returns full record (including TLEs) for one satellite."""
    with get_conn() as conn:
        row  = conn.execute(
            "SELECT * FROM satellites WHERE norad_id = ?", (norad_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Satellite not found")
    return dict(row)


# ── Orbit Propagation ─────────────────────────────────────────────────────────

@app.get("/position/{norad_id}")
def current_position(norad_id: str):
    """Current ECI position + velocity + geodetic coords via SGP4."""
    with get_conn() as conn:
        row  = conn.execute(
            "SELECT tle1, tle2 FROM satellites WHERE norad_id = ?", (norad_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Satellite not found")
    result = get_position(row["tle1"], row["tle2"])
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.get("/orbit/{norad_id}")
def orbit_track(
    norad_id: str,
    hours: float = Query(default=24, ge=0.1, le=72),
    step: int = Query(default=60, ge=10, le=3600)
):
    """Orbit geodetic track sampled every `step` seconds."""
    with get_conn() as conn:
        row  = conn.execute(
            "SELECT tle1, tle2 FROM satellites WHERE norad_id = ?", (norad_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Satellite not found")
    track = get_orbit_track(row["tle1"], row["tle2"], hours=hours, step_seconds=step)
    return {"norad_id": norad_id, "hours": hours, "step_seconds": step,
            "points": len(track), "track": track}


# ── Batch positions (parallelised) ────────────────────────────────────────────

# In-memory cache for /positions/all to avoid recomputing SGP4 on every request
_positions_cache: dict = {
    "data": None,
    "timestamp": 0.0,
    "ttl": POSITIONS_CACHE_TTL_S,
}
_positions_cache_lock = threading.Lock()


def _compute_one(row: dict) -> dict | None:
    pos = get_position(row["tle1"], row["tle2"])
    if pos.get("error"):
        return None
    return {
        "norad_id": row["norad_id"],
        "name":     row["name"],
        "category": row.get("category"),
        "lat":      pos["geo"]["lat"],
        "lon":      pos["geo"]["lon"],
        "alt":      pos["geo"]["alt"],
        "speed":    pos["velocity"]["speed_km_s"],
    }


def _invalidate_positions_cache():
    """Clear the positions cache — call after TLE fetch or detection runs."""
    with _positions_cache_lock:
        _positions_cache["data"] = None
        _positions_cache["timestamp"] = 0.0


@app.get("/positions/all")
def all_positions(category: str = Query(default="", max_length=50)):
    """
    Batch-computes current positions for all satellites in parallel.
    Uses a 15-second TTL cache to avoid redundant SGP4 computations.
    """
    now = time.time()

    # Check cache first (only for unfiltered requests)
    if not category:
        with _positions_cache_lock:
            if (_positions_cache["data"] is not None and
                    now - _positions_cache["timestamp"] < _positions_cache["ttl"]):
                return _positions_cache["data"]

    with get_conn() as conn:
        if category:
            rows = [dict(r) for r in conn.execute(
                "SELECT norad_id, name, category, tle1, tle2 FROM satellites WHERE category = ?",
                (category,),
            ).fetchall()]
        else:
            rows = [dict(r) for r in conn.execute(
                "SELECT norad_id, name, category, tle1, tle2 FROM satellites"
            ).fetchall()]

    if not rows:
        return {"count": 0, "satellites": []}

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(rows))) as pool:
        results = list(pool.map(_compute_one, rows))

    sats = [r for r in results if r is not None]
    response = {"count": len(sats), "satellites": sats}

    # Cache the result for unfiltered requests
    if not category:
        with _positions_cache_lock:
            _positions_cache["data"] = response
            _positions_cache["timestamp"] = now

    return response


# ── Conjunction Detection ─────────────────────────────────────────────────────

# Cache for satellite names (rarely changes, avoids full table scan)
_sat_names_cache: dict = {"data": None, "count": 0}
_sat_names_lock = threading.Lock()


def _get_sat_names() -> dict:
    """Get cached satellite name lookup, refreshing only when count changes."""
    with get_conn() as conn:
        current_count = conn.execute("SELECT COUNT(*) FROM satellites").fetchone()[0]

    with _sat_names_lock:
        if _sat_names_cache["data"] is None or _sat_names_cache["count"] != current_count:
            with get_conn() as conn:
                _sat_names_cache["data"] = {
                    r["norad_id"]: r["name"]
                    for r in conn.execute("SELECT norad_id, name FROM satellites").fetchall()
                }
            _sat_names_cache["count"] = current_count
        return _sat_names_cache["data"]


def _invalidate_all_caches():
    """Clear all caches — call after TLE fetch or DB changes."""
    _invalidate_positions_cache()
    with _sat_names_lock:
        _sat_names_cache["data"] = None
        _sat_names_cache["count"] = 0


@app.post("/detect")
def detect_conjunctions(
    hours: float = Query(default=24, ge=0.5, le=72),
    step: int = Query(default=120, ge=30, le=3600),
    threshold: float = Query(default=200.0, ge=0.1, le=1000.0)
):
    """
    Run the full conjunction detection pipeline.
    """
    try:
        result = run_detection(hours=hours, step_seconds=step, threshold_km=threshold)
        _state["last_detect_at"] = datetime.now(timezone.utc).isoformat()
        _invalidate_all_caches()
        return result
    except Exception as e:
        logger.error(f"Manual detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conjunctions")
def get_conjunctions(
    risk: str = Query(default="", max_length=20),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Stored conjunction events, optionally filtered by risk level (HIGH/MEDIUM/LOW)."""
    sat_names = _get_sat_names()

    with get_conn() as conn:
        if risk:
            rows = conn.execute(
                "SELECT sat1, sat2, tca, distance, velocity, risk FROM conjunctions "
                "WHERE risk = ? ORDER BY distance ASC LIMIT ?",
                (risk.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT sat1, sat2, tca, distance, velocity, risk FROM conjunctions "
                "ORDER BY distance ASC LIMIT ?",
                (limit,),
            ).fetchall()

        total = conn.execute("SELECT COUNT(*) FROM conjunctions").fetchone()[0]

    events = [
        {
            "sat1":      r["sat1"],
            "sat1_name": sat_names.get(r["sat1"], r["sat1"]),
            "sat2":      r["sat2"],
            "sat2_name": sat_names.get(r["sat2"], r["sat2"]),
            "tca":       r["tca"],
            "distance":  r["distance"],
            "velocity":  r["velocity"],
            "risk":      r["risk"],
        }
        for r in rows
    ]
    return {"total": total, "events": events}


# ── Proximity pairs (for globe arc visualisation) ─────────────────────────────

# Cache for proximity results (expensive SGP4 + KD-Tree computation)
_proximity_cache: dict = {
    "data": None,
    "timestamp": 0.0,
    "ttl": PROXIMITY_CACHE_TTL_S,
}
_proximity_cache_lock = threading.Lock()


@app.get("/proximity")
def get_proximity(limit: int = Query(default=200, ge=1, le=500)):
    """
    Returns the `limit` closest satellite pairs based on their current positions.
    """
    now = time.time()

    # Check cache first
    with _proximity_cache_lock:
        if (_proximity_cache["data"] is not None and
                now - _proximity_cache["timestamp"] < _proximity_cache["ttl"]):
            return _proximity_cache["data"]

    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT norad_id, name, tle1, tle2 FROM satellites"
        ).fetchall()]

    if not rows:
        return {"count": 0, "pairs": []}

    # ── 1. Propagate all satellites to now ───────────────────────────────────
    def _prop(row: dict):
        pos = get_position(row["tle1"], row["tle2"])
        if pos.get("error"):
            return None
        return {
            "norad_id": row["norad_id"],
            "name":     row["name"],
            "lat":      pos["geo"]["lat"],
            "lon":      pos["geo"]["lon"],
            "x":        pos["eci"]["x"],
            "y":        pos["eci"]["y"],
            "z":        pos["eci"]["z"],
        }

    workers = min(MAX_WORKERS, len(rows))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_prop, rows))

    valid = [r for r in results if r is not None]
    if len(valid) < 2:
        return {"count": 0, "pairs": []}

    # ── 2. Build KD-Tree on ECI positions ────────────────────────────────────
    positions = np.array([[v["x"], v["y"], v["z"]] for v in valid], dtype=np.float64)
    tree = cKDTree(positions)

    # Query each point for its nearest neighbours (excluding itself)
    k = min(KNN_NEIGHBORS, len(valid))
    distances, indices = tree.query(positions, k=k)

    # ── 3. Collect unique pairs sorted by distance ────────────────────────────
    seen: set[tuple] = set()
    pairs: list[dict] = []

    for i, (dists, idxs) in enumerate(zip(distances, indices)):
        for dist, j in zip(dists[1:], idxs[1:]):   # skip self (index 0)
            key = (min(i, j), max(i, j))
            if key in seen:
                continue
            seen.add(key)
            pairs.append({
                "sat1":       valid[i]["norad_id"],
                "sat1_name":  valid[i]["name"],
                "sat1_lat":   valid[i]["lat"],
                "sat1_lon":   valid[i]["lon"],
                "sat2":       valid[j]["norad_id"],
                "sat2_name":  valid[j]["name"],
                "sat2_lat":   valid[j]["lat"],
                "sat2_lon":   valid[j]["lon"],
                "distance":   round(float(dist), 2),
                "risk":       risk_label(float(dist)),
            })

    pairs.sort(key=lambda p: p["distance"])
    pairs = pairs[:limit]

    response = {"count": len(pairs), "pairs": pairs}

    # Cache the result
    with _proximity_cache_lock:
        _proximity_cache["data"] = response
        _proximity_cache["timestamp"] = now

    return response


# ── AI Analysis ─────────────────────────────────────────────────────────────────────

class ConjunctionAnalysisRequest(BaseModel):
    sat1: str = Field(..., min_length=1)
    sat2: str = Field(..., min_length=1)
    distance_km: float = Field(..., ge=0)
    velocity_kms: float = Field(default=0, ge=0)
    tca: str = Field(default="")


@app.post("/ai/analyze-conjunction")
def ai_analyze_conjunction(payload: ConjunctionAnalysisRequest):
    """
    Analyze a single conjunction event using OpenRouter AI.
    """
    return analyze_conjunction(
        payload.sat1,
        payload.sat2,
        payload.distance_km,
        payload.velocity_kms,
        payload.tca
    )


@app.get("/ai/summary")
def ai_summary(limit: int = Query(default=10, ge=1, le=50)):
    """
    Get AI summary of top risk conjunctions from stored events.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT sat1, sat2, distance, risk FROM conjunctions "
            "ORDER BY distance ASC LIMIT ?",
            (limit,),
        ).fetchall()

    if not rows:
        return {"summaries": []}

    conjunctions = [
        {"sat1": r["sat1"], "sat2": r["sat2"], "distance": r["distance"], "risk": r["risk"]}
        for r in rows
    ]

    return summarize_top_risks(conjunctions, count=3)
