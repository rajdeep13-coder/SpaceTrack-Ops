// ── Shared TypeScript types for SpaceTrackOps ─────────────────────────────────

export interface Satellite {
  norad_id: string;
  name: string;
  category?: string;
  last_updated: string;
}

export interface Position {
  timestamp: string;
  eci: { x: number; y: number; z: number };
  velocity: { vx: number; vy: number; vz: number; speed_km_s: number };
  geo: { lat: number; lon: number; alt: number };
  distance_from_center_km: number;
  error: string | null;
}

export interface ConjunctionEvent {
  sat1: string;
  sat1_name: string;
  sat2: string;
  sat2_name: string;
  tca: string;
  distance: number;
  velocity: number;
  risk: "HIGH" | "MEDIUM" | "LOW";
}

export interface AIConjunctionAnalysis {
  risk_summary: string;
  recommendation: string;
  explanation: string;
}

export interface SystemStatus {
  satellites: number;
  conjunctions: number;
  last_fetch_at: string | null;
  last_detect_at: string | null;
  runs_completed: number;
  auto_refresh_active: boolean;
  scheduler_running: boolean;
  next_scheduled: string | null;
}

export interface CategoryInfo {
  name: string;
  count: number;
}

export interface SatPoint {
  norad_id: string;
  name: string;
  lat: number;
  lon: number;
  alt: number;
  speed: number;
  category?: string;
  riskLevel: "HIGH" | "MEDIUM" | "NONE";
}

export interface OrbitPoint {
  lat: number;
  lon: number;
  alt: number;
}

export interface ConjArc {
  sat1_name: string;
  sat2_name: string;
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  risk: "HIGH" | "MEDIUM" | "LOW";
  distance: number;
  layer?: string;
}

export interface ProximityPair {
  sat1: string;
  sat1_name: string;
  sat1_lat: number;
  sat1_lon: number;
  sat2: string;
  sat2_name: string;
  sat2_lat: number;
  sat2_lon: number;
  distance: number;
  risk: "HIGH" | "MEDIUM" | "LOW";
}

export interface PathDatum {
  pts: [number, number, number][];
  type: "grid" | "orbit" | "track";
}

export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";
export type RiskFilter = "" | RiskLevel;
