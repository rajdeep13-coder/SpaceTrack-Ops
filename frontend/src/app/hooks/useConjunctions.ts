"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL, DEFAULT_CONJUNCTION_LIMIT } from "../config";
import type { ConjunctionEvent, RiskFilter } from "../types";

export function useConjunctions() {
  const [conjunctions, setConjunctions] = useState<ConjunctionEvent[]>([]);
  const [conjTotal, setConjTotal] = useState(0);
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("");
  const [loadingConj, setLoadingConj] = useState(false);

  const loadConjunctions = useCallback(async (risk: string) => {
    setLoadingConj(true);
    try {
      const url = new URL(`${API_BASE_URL}/conjunctions`);
      url.searchParams.set("limit", String(DEFAULT_CONJUNCTION_LIMIT));
      if (risk) url.searchParams.set("risk", risk);
      const d = await (await fetch(url.toString())).json();
      setConjunctions(d.events ?? []);
      setConjTotal(d.total ?? 0);
    } catch (err) {
      console.error("[useConjunctions] Failed to load conjunctions:", err);
      setConjunctions([]);
    } finally {
      setLoadingConj(false);
    }
  }, []);

  useEffect(() => {
    loadConjunctions(riskFilter);
  }, [riskFilter, loadConjunctions]);

  return { conjunctions, conjTotal, riskFilter, setRiskFilter, loadingConj, loadConjunctions };
}
