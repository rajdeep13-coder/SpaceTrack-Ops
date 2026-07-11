// ── SpaceTrackOps configuration constants ─────────────────────────────────────

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// Polling intervals
export const STATUS_POLL_INTERVAL_MS = 30_000;
export const POSITION_POLL_INTERVAL_MS = 5_000;
export const DATA_REFRESH_INTERVAL_MS = 30_000;
export const SEARCH_DEBOUNCE_MS = 300;
export const TOAST_DURATION_MS = 5_000;

// API limits
export const DEFAULT_CONJUNCTION_LIMIT = 200;
export const DEFAULT_SEARCH_LIMIT = 50;
export const DEFAULT_PROXIMITY_LIMIT = 300;
export const ORBIT_TRACK_HOURS = 2;
export const ORBIT_TRACK_STEP_S = 30;

// Styling constants
export const RISK_STYLE = {
  HIGH: {
    pill: "bg-red-950 text-red-300 border-red-700",
    dot: "bg-red-400",
    card: "border-red-800/60 bg-red-950/30",
  },
  MEDIUM: {
    pill: "bg-yellow-950 text-yellow-300 border-yellow-700",
    dot: "bg-yellow-400",
    card: "border-yellow-800/50 bg-yellow-950/20",
  },
  LOW: {
    pill: "bg-zinc-800 text-zinc-400 border-zinc-700",
    dot: "bg-zinc-500",
    card: "border-zinc-800 bg-zinc-900/40",
  },
} as const;

export const CAT_COLOR: Record<string, string> = {
  starlink: "#818cf8",
  stations: "#22d3ee",
  active: "#4ade80",
  debris: "#f87171",
  oneweb: "#fb923c",
  planet: "#a78bfa",
  spire: "#34d399",
};

export function catColor(cat?: string): string {
  if (!cat) return "#4ade80";
  return CAT_COLOR[cat.toLowerCase()] ?? "#4ade80";
}

// ── Helpers ───────────────────────────────────────────────────────────────────

export function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ${m % 60}m ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function timeUntil(iso: string | null): string {
  if (!iso) return "—";
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return "soon";
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

export function fmtCoord(v: number, pos: string, neg: string): string {
  return `${Math.abs(v).toFixed(4)}° ${v >= 0 ? pos : neg}`;
}
