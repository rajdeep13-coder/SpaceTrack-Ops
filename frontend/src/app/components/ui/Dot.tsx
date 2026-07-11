"use client";

export function Dot({ color }: { color: string }) {
  return (
    <span
      className="w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse inline-block"
      style={{ background: color }}
    />
  );
}
