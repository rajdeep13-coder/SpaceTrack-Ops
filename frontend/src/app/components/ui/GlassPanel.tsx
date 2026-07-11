"use client";

import React from "react";

export function GlassPanel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-black/70 backdrop-blur-xl border border-white/10 rounded-2xl ${className}`}
    >
      {children}
    </div>
  );
}
