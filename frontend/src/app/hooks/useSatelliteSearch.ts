"use client";

import { useState, useEffect } from "react";
import { API_BASE_URL, DEFAULT_SEARCH_LIMIT, SEARCH_DEBOUNCE_MS } from "../config";
import type { Satellite } from "../types";

export function useSatelliteSearch() {
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Satellite[]>([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    if (!search.trim()) {
      setSearchResults([]);
      setSearchTotal(0);
      return;
    }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const url = new URL(`${API_BASE_URL}/satellites`);
        url.searchParams.set("limit", String(DEFAULT_SEARCH_LIMIT));
        url.searchParams.set("search", search.trim());
        const d = await (await fetch(url.toString())).json();
        setSearchResults(d.satellites ?? []);
        setSearchTotal(d.total ?? 0);
      } catch (err) {
        console.error("[useSatelliteSearch] Search failed:", err);
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [search]);

  return { search, setSearch, searchResults, searchTotal, searching, showSearch, setShowSearch };
}
