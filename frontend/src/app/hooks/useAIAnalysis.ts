"use client";

import { useState, useCallback } from "react";
import { API_BASE_URL } from "../config";
import type { ConjunctionEvent, AIConjunctionAnalysis } from "../types";

export function useAIAnalysis() {
  const [aiAnalysis, setAiAnalysis] = useState<AIConjunctionAnalysis | null>(null);
  const [loadingAI, setLoadingAI] = useState(false);
  const [selectedConj, setSelectedConj] = useState<ConjunctionEvent | null>(null);

  const fetchAIAnalysis = useCallback(async (conj: ConjunctionEvent) => {
    setLoadingAI(true);
    setSelectedConj(conj);
    setAiAnalysis(null);
    try {
      const res = await fetch(`${API_BASE_URL}/ai/analyze-conjunction`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sat1: conj.sat1_name,
          sat2: conj.sat2_name,
          distance_km: conj.distance,
          velocity_kms: conj.velocity,
          tca: conj.tca,
        }),
      });
      if (res.ok) {
        const d = await res.json();
        setAiAnalysis(d);
      }
    } catch (err) {
      console.error("[useAIAnalysis] Failed to fetch AI analysis:", err);
    } finally {
      setLoadingAI(false);
    }
  }, []);

  return { aiAnalysis, loadingAI, selectedConj, fetchAIAnalysis };
}
