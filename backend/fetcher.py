"""
fetcher.py — SpaceTrackOps TLE ingestion
Pulls from multiple CelesTrak groups in parallel using ThreadPoolExecutor.
Each satellite is tagged with a category derived from its source group.
Groups that fail (HTTP error, timeout, parse error) are skipped gracefully.
"""

import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from db import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Group definitions: (celestrak_group_name, category_label)
# ---------------------------------------------------------------------------
GROUPS: list[tuple[str, str]] = [
    ("active",              "active"),
    ("stations",            "stations"),
    ("starlink",            "starlink"),
    ("oneweb",              "oneweb"),
    ("planet",              "planet"),
    ("spire",               "spire"),
    ("cosmos-2251-debris",  "debris"),
    ("iridium-33-debris",   "debris"),
    ("fengyun-1c-debris",   "debris"),
]

BASE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_tles(raw_text: str, category: str) -> list[dict]:
    """
    Parse a raw TLE text block into a list of satellite dicts.
    Expects groups of 3 lines: name / TLE line 1 / TLE line 2.
    Invalid triplets are silently skipped.
    """
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
    satellites: list[dict] = []

    for i in range(0, len(lines) - 2, 3):
        name = lines[i]
        tle1 = lines[i + 1]
        tle2 = lines[i + 2]

        if not tle1.startswith("1 ") or not tle2.startswith("2 "):
            continue

        norad_id = tle1[2:7].strip()
        satellites.append({
            "name":     name,
            "norad_id": norad_id,
            "tle1":     tle1,
            "tle2":     tle2,
            "category": category,
        })

    return satellites

# ---------------------------------------------------------------------------
# Per-group fetch (runs in a thread)
# ---------------------------------------------------------------------------

def _fetch_group(group: str, category: str) -> list[dict]:
    """
    Download and parse TLEs for a single CelesTrak group.
    Returns an empty list (and logs) on any error so the caller can continue.
    """
    url = BASE_URL.format(group=group)
    try:
        logger.info(f"Fetching group '{group}' ({category}) ...")
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        sats = parse_tles(response.text, category)
        logger.info(f"Group '{group}': {len(sats)} satellites parsed.")
        return sats
    except requests.exceptions.HTTPError as exc:
        logger.error(f"HTTP error for group '{group}': {exc} — skipping.")
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout for group '{group}' — skipping.")
    except requests.exceptions.RequestException as exc:
        logger.error(f"Network error for group '{group}': {exc} — skipping.")
    except Exception as exc:
        logger.error(f"Unexpected error for group '{group}': {exc} — skipping.")
    return []

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fetch_and_store() -> dict:
    """
    Fetch TLEs from all configured CelesTrak groups in parallel, deduplicate
    by NORAD ID (last writer wins when the same object appears in multiple
    groups), then upsert every satellite into the database.

    Returns a summary dict with total counts and a per-category breakdown.
    """
    # ── 1. Parallel download ─────────────────────────────────────────────────
    all_sats: list[dict] = []

    with ThreadPoolExecutor(max_workers=len(GROUPS)) as pool:
        future_to_group = {
            pool.submit(_fetch_group, group, category): (group, category)
            for group, category in GROUPS
        }
        for future in as_completed(future_to_group):
            group, category = future_to_group[future]
            try:
                sats = future.result()
                all_sats.extend(sats)
            except Exception as exc:
                # Belt-and-suspenders; _fetch_group already catches internally
                logger.error(f"Unhandled future error for '{group}': {exc}")

    if not all_sats:
        return {
            "status":    "error",
            "message":   "No satellites parsed from any group",
            "total":     0,
            "inserted":  0,
            "updated":   0,
            "by_category": {},
        }

    # ── 2. Deduplicate: if a NORAD ID appears in multiple groups, keep the
    #       entry whose category is most specific (preserve first-seen order
    #       then let later groups overwrite — "active" tends to come first so
    #       a more-specific group like "starlink" that arrives later wins).
    seen: dict[str, dict] = {}
    for sat in all_sats:
        seen[sat["norad_id"]] = sat   # later group overwrites earlier
    unique_sats = list(seen.values())

    logger.info(f"{len(all_sats)} total parsed, {len(unique_sats)} unique by NORAD ID.")

    # ── 3. Upsert into DB ────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated  = 0

    with get_conn() as conn:
        cursor = conn.cursor()
        for sat in unique_sats:
            existing = cursor.execute(
                "SELECT id FROM satellites WHERE norad_id = ?", (sat["norad_id"],)
            ).fetchone()

            if existing:
                cursor.execute(
                    """UPDATE satellites
                          SET name = ?, tle1 = ?, tle2 = ?, category = ?, last_updated = ?
                        WHERE norad_id = ?""",
                    (sat["name"], sat["tle1"], sat["tle2"],
                     sat["category"], now, sat["norad_id"]),
                )
                updated += 1
            else:
                cursor.execute(
                    """INSERT INTO satellites (norad_id, name, tle1, tle2, category, last_updated)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (sat["norad_id"], sat["name"], sat["tle1"], sat["tle2"],
                     sat["category"], now),
                )
                inserted += 1
        conn.commit()

    # ── 4. Build per-category summary ────────────────────────────────────────
    by_category: dict[str, int] = {}
    for sat in unique_sats:
        cat = sat["category"] or "unknown"
        by_category[cat] = by_category.get(cat, 0) + 1

    result = {
        "status":      "ok",
        "total":       len(unique_sats),
        "inserted":    inserted,
        "updated":     updated,
        "fetched_at":  now,
        "by_category": by_category,
    }
    logger.info(f"Done: {result}")
    return result
