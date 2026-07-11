"use client";

import { RISK_STYLE } from "../../config";
import type { RiskLevel } from "../../types";

export function RiskPill({ risk }: { risk: RiskLevel }) {
  const s = RISK_STYLE[risk];
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[10px] font-bold tracking-widest px-2 py-0.5 rounded-full border ${s.pill}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot} animate-pulse`} />
      {risk}
    </span>
  );
}
