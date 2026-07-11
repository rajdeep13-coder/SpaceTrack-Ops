"""
detector.py — Pairwise conjunction detection with scipy KD-Tree optimisation.

Phase 6 upgrade:
  - scipy.spatial.cKDTree replaces the O(n²) inner loop.
  - At each time step we only examine pairs spatially close to the threshold,
    giving O(n log n + k) per step (k = number of close pairs).
  - For n < 80 we fall back to the pure-Python loop (tree overhead not worth it).
  - concurrent.futures.ThreadPoolExecutor parallelises track propagation.

Pipeline (unchanged interface):
  run_detection() → loads sats → compute_tracks() → find_conjunctions() →
  stores results → returns summary dict
"""

import logging
import math
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import numpy as np
from scipy.spatial import cKDTree
from sgp4.api import Satrec

from db import get_conn
from utils import jd_fr, risk_label

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_THRESHOLD_KM = 200.0   # Wide net — real SSA systems warn at 200 km+
DEFAULT_HOURS        = 24
DEFAULT_STEP_S       = 120     # 2-min steps — fast enough for 17k sats

# KD-Tree is only worth it above this satellite count
KDTREE_MIN_N = 60

# Max workers for parallel propagation (tune to CPU count)
MAX_WORKERS = 8


# ── Track computation (parallelised) ─────────────────────────────────────────

def _propagate_one(
    sat: dict,
    t_start: datetime,
    n_steps: int,
    step_seconds: int,
) -> list[tuple]:
    """Propagate a single satellite. Called from a thread pool."""
    satrec = Satrec.twoline2rv(sat["tle1"], sat["tle2"])
    points: list[tuple] = []
    for i in range(n_steps):
        t = t_start + timedelta(seconds=i * step_seconds)
        jd, fr = jd_fr(t)
        err, r, v = satrec.sgp4(jd, fr)
        if err == 0:
            points.append((t.isoformat(), r[0], r[1], r[2], v[0], v[1], v[2]))
    return points


def compute_tracks(
    satellites: list[dict],
    hours: float       = DEFAULT_HOURS,
    step_seconds: int  = DEFAULT_STEP_S,
    t_start: datetime | None = None,
) -> dict[str, list[tuple]]:
    """
    Propagate all satellites in parallel using a thread pool.
    Returns {norad_id: [(timestamp_iso, x, y, z, vx, vy, vz), ...]}
    """
    if t_start is None:
        t_start = datetime.now(timezone.utc)

    n_steps  = int(hours * 3600 / step_seconds)
    workers  = min(MAX_WORKERS, len(satellites))
    tracks: dict[str, list] = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_propagate_one, sat, t_start, n_steps, step_seconds): sat["norad_id"]
            for sat in satellites
        }
        for fut in as_completed(futures):
            nid = futures[fut]
            tracks[nid] = fut.result()

    return tracks


# ── KD-Tree conjunction search ────────────────────────────────────────────────

def _find_conjunctions_kdtree(
    tracks: dict[str, list],
    sats_by_id: dict,
    threshold_km: float,
) -> list[dict]:
    """
    For each time step, build a cKDTree of ECI positions and find all pairs
    within threshold_km.  Tracks the step with minimum distance for each
    conjunction.
    """
    valid_tracks = {nid: t for nid, t in tracks.items() if len(t) > 0}
    norad_ids = list(valid_tracks.keys())

    # min_dist[(i,j)] = (distance, step_index)  where i < j
    min_dist: dict[tuple, tuple] = {}

    n_steps = min((len(valid_tracks[nid]) for nid in norad_ids), default=0)

    for k in range(n_steps):
        # Build position matrix
        pos_list, valid_idx = [], []
        for idx, nid in enumerate(norad_ids):
            pt = valid_tracks[nid][k]
            pos_list.append([pt[1], pt[2], pt[3]])
            valid_idx.append(idx)

        if len(pos_list) < 2:
            continue

        pos = np.asarray(pos_list, dtype=np.float64)
        tree = cKDTree(pos)

        # query_pairs returns indices LOCAL to pos_list
        for (li, lj) in tree.query_pairs(threshold_km):
            gi, gj = valid_idx[li], valid_idx[lj]
            key = (min(gi, gj), max(gi, gj))
            d = float(np.linalg.norm(pos[li] - pos[lj]))
            if key not in min_dist or d < min_dist[key][0]:
                min_dist[key] = (d, k)

    return _build_events(tracks, norad_ids, sats_by_id, min_dist, threshold_km)


def _find_conjunctions_naive(
    tracks: dict[str, list],
    sats_by_id: dict,
    threshold_km: float,
) -> list[dict]:
    """
    Pure-Python O(n² × n_steps) brute force.
    Faster than KD-Tree for small n due to lower constant factor.
    """
    norad_ids = list(tracks.keys())
    n         = len(norad_ids)
    min_dist: dict[tuple, tuple] = {}

    for i in range(n):
        for j in range(i + 1, n):
            key    = (i, j)
            track1 = tracks[norad_ids[i]]
            track2 = tracks[norad_ids[j]]
            steps  = min(len(track1), len(track2))
            best_d, best_k = float("inf"), -1

            for k in range(steps):
                dx = track1[k][1] - track2[k][1]
                dy = track1[k][2] - track2[k][2]
                dz = track1[k][3] - track2[k][3]
                d  = math.sqrt(dx*dx + dy*dy + dz*dz)
                if d < best_d:
                    best_d, best_k = d, k

            if best_d < threshold_km:
                min_dist[key] = (best_d, best_k)

    return _build_events(tracks, norad_ids, sats_by_id, min_dist, threshold_km)


def _build_events(
    tracks: dict,
    norad_ids: list,
    sats_by_id: dict,
    min_dist: dict,
    threshold_km: float,
) -> list[dict]:
    """Convert (i,j) → (distance, step) mapping into output event dicts."""
    MIN_REAL_CONJ_DIST = 0.5   # km — below this, likely docked
    MIN_REAL_CONJ_VEL  = 0.5   # km/s — below this, likely formation flying

    events = []
    for (i, j), (dist, k) in min_dist.items():
        if dist >= threshold_km:
            continue
        nid1, nid2 = norad_ids[i], norad_ids[j]
        pt1, pt2   = tracks[nid1][k], tracks[nid2][k]
        rel_vel    = math.sqrt(
            (pt1[4]-pt2[4])**2 + (pt1[5]-pt2[5])**2 + (pt1[6]-pt2[6])**2
        )
        # Skip docked/formation pairs
        if dist < MIN_REAL_CONJ_DIST and rel_vel < MIN_REAL_CONJ_VEL:
            continue
        events.append({
            "sat1":      nid1,
            "sat1_name": sats_by_id[nid1]["name"],
            "sat2":      nid2,
            "sat2_name": sats_by_id[nid2]["name"],
            "tca":       pt1[0],
            "distance":  round(dist, 4),
            "velocity":  round(rel_vel, 4),
            "risk":      risk_label(dist),
        })
    return sorted(events, key=lambda e: e["distance"])


def find_conjunctions(
    tracks: dict[str, list],
    sats_by_id: dict,
    threshold_km: float = DEFAULT_THRESHOLD_KM,
) -> list[dict]:
    """Dispatcher: chooses KD-Tree or naive based on satellite count."""
    n = len(tracks)
    if n >= KDTREE_MIN_N:
        logger.info(f"Using KD-Tree search (n={n})")
        return _find_conjunctions_kdtree(tracks, sats_by_id, threshold_km)
    else:
        logger.info(f"Using naive search (n={n} < {KDTREE_MIN_N})")
        return _find_conjunctions_naive(tracks, sats_by_id, threshold_km)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_detection(
    hours: float        = DEFAULT_HOURS,
    step_seconds: int   = DEFAULT_STEP_S,
    threshold_km: float = DEFAULT_THRESHOLD_KM,
) -> dict:
    """Full conjunction detection pipeline."""
    t0 = datetime.now(timezone.utc)

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT norad_id, name, tle1, tle2 FROM satellites"
        ).fetchall()

    satellites  = [dict(r) for r in rows]
    sats_by_id  = {s["norad_id"]: s for s in satellites}
    n_pairs     = len(satellites) * (len(satellites) - 1) // 2

    logger.info(f"Propagating {len(satellites)} satellites "
                f"({int(hours * 3600 / step_seconds)} steps, {MAX_WORKERS} workers)…")

    tracks = compute_tracks(satellites, hours=hours, step_seconds=step_seconds)

    logger.info(f"Checking {n_pairs} pairs (threshold={threshold_km} km)…")
    events = find_conjunctions(tracks, sats_by_id, threshold_km=threshold_km)

    # Persist
    with get_conn() as conn:
        cursor  = conn.cursor()
        cursor.execute("DELETE FROM conjunctions")
        for ev in events:
            cursor.execute(
                "INSERT INTO conjunctions (sat1, sat2, tca, distance, velocity, risk) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ev["sat1"], ev["sat2"], ev["tca"],
                 ev["distance"], ev["velocity"], ev["risk"]),
            )
        conn.commit()

    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    logger.info(f"Done — {len(events)} conjunctions stored in {elapsed:.2f}s")

    return {
        "status":              "ok",
        "satellites_analyzed": len(satellites),
        "pairs_checked":       n_pairs,
        "hours_window":        hours,
        "step_seconds":        step_seconds,
        "threshold_km":        threshold_km,
        "conjunctions_found":  len(events),
        "elapsed_seconds":     round(elapsed, 3),
        "events":              events,
    }


if __name__ == "__main__":
    import json, time
    logging.basicConfig(level=logging.INFO)
    t0     = time.time()
    result = run_detection()
    logger.info(f"Completed in {time.time()-t0:.2f}s")
    print(json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2))
