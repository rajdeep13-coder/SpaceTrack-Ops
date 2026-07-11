"use client";

import { useState, useCallback } from "react";
import { API_BASE_URL, TOAST_DURATION_MS } from "../config";

export function useActions(
  fetchStatus: () => Promise<void>,
  loadConjunctions: (risk: string) => Promise<void>,
  riskFilter: string,
) {
  const [fetching, setFetching] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const showToast = useCallback((msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), TOAST_DURATION_MS);
  }, []);

  const triggerFetch = async () => {
    setFetching(true);
    try {
      const d = await (await fetch(`${API_BASE_URL}/fetch`, { method: "POST" })).json();
      showToast(
        `Fetched ${d.total?.toLocaleString()} satellites — ${d.inserted} new, ${d.updated} updated`,
      );
      await fetchStatus();
    } catch (err) {
      console.error("[useActions] Fetch TLEs failed:", err);
      showToast("Failed to reach CelesTrak", false);
    } finally {
      setFetching(false);
    }
  };

  const runDetection = async () => {
    setDetecting(true);
    try {
      const d = await (await fetch(`${API_BASE_URL}/detect`, { method: "POST" })).json();
      showToast(
        `${d.conjunctions_found} conjunctions found across ${d.satellites_analyzed} sats in ${d.elapsed_seconds}s`,
      );
      await Promise.all([loadConjunctions(riskFilter), fetchStatus()]);
    } catch (err) {
      console.error("[useActions] Detection failed:", err);
      showToast("Detection failed", false);
    } finally {
      setDetecting(false);
    }
  };

  return { fetching, detecting, toast, setToast, showToast, triggerFetch, runDetection };
}
