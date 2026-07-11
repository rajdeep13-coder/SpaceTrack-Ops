"""
utils.py — Shared utilities for SpaceTrackOps backend
"""

import math
from datetime import datetime
from sgp4.api import jday

# Earth constants
R_EARTH = 6378.137  # Equatorial radius (km)
F_EARTH = 1 / 298.257223563  # Flattening


def jd_fr(t: datetime) -> tuple[float, float]:
    """Convert a UTC datetime to Julian date + fraction."""
    return jday(
        t.year, t.month, t.day,
        t.hour, t.minute, t.second + t.microsecond / 1e6,
    )


def risk_label(distance_km: float) -> str:
    """
    Risk classification aligned with real SSA warning thresholds:
      HIGH   < 10 km  — immediate conjunction warning
      MEDIUM < 50 km  — close approach, monitor closely
      LOW    < 200 km — proximity alert, low risk
    """
    if distance_km < 10.0:
        return "HIGH"
    if distance_km < 50.0:
        return "MEDIUM"
    return "LOW"
