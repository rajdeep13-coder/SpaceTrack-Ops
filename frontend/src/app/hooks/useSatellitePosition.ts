"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE_URL, POSITION_POLL_INTERVAL_MS } from "../config";
import type { Satellite, Position } from "../types";

export function useSatellitePosition(selected: Satellite | null) {
  const [position, setPosition] = useState<Position | null>(null);
  const [posLoading, setPosLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPosition = useCallback(async (norad_id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/position/${norad_id}`);
      if (res.ok) setPosition(await res.json());
    } catch (err) {
      console.error("[useSatellitePosition] Failed to fetch position:", err);
    }
  }, []);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (!selected) {
      setPosition(null);
      return;
    }
    setPosLoading(true);
    fetchPosition(selected.norad_id).finally(() => setPosLoading(false));
    pollRef.current = setInterval(() => fetchPosition(selected.norad_id), POSITION_POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [selected, fetchPosition]);

  return { position, posLoading };
}
