"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL, STATUS_POLL_INTERVAL_MS } from "../config";
import type { SystemStatus, CategoryInfo } from "../types";

export function useBackendStatus() {
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [sysStatus, setSysStatus] = useState<SystemStatus | null>(null);
  const [categories, setCategories] = useState<CategoryInfo[]>([]);

  const fetchStatus = useCallback(async () => {
    try {
      const [r1, r2, r3] = await Promise.all([
        fetch(`${API_BASE_URL}/`),
        fetch(`${API_BASE_URL}/status`),
        fetch(`${API_BASE_URL}/satellites/categories`),
      ]);
      setBackendOk(r1.ok);
      if (r2.ok) setSysStatus(await r2.json());
      if (r3.ok) {
        const d = await r3.json();
        setCategories(d.categories ?? []);
      }
    } catch (err) {
      console.error("[useBackendStatus] Failed to fetch status:", err);
      setBackendOk(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, STATUS_POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchStatus]);

  return { backendOk, sysStatus, categories, fetchStatus };
}
