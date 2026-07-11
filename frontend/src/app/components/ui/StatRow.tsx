"use client";

export function StatRow({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string | number;
  unit?: string;
  accent?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
      <span className="text-[10px] uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <span
        className={`font-mono text-xs font-semibold ${accent ? "text-cyan-300" : "text-zinc-200"}`}
      >
        {value}
        {unit && <span className="text-zinc-500 font-normal ml-1">{unit}</span>}
      </span>
    </div>
  );
}
