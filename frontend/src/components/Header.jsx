import React from "react";

export default function Header({ modelName, lastUpdated }) {
  return (
    <header className="flex items-center justify-between border-b border-char-border px-6 py-4">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-ember flex items-center justify-center font-display font-bold text-char-950">
          E
        </div>
        <div>
          <h1 className="font-display text-2xl font-extrabold tracking-wide leading-none">EMBER</h1>
          <p className="text-[11px] font-mono text-ink-faint tracking-wide">
            forest fire risk intelligence
          </p>
        </div>
      </div>
      <div className="flex items-center gap-4 text-right">
        {modelName && (
          <div className="hidden sm:block">
            <p className="text-[10px] font-mono text-ink-faint uppercase tracking-wide">active model</p>
            <p className="text-sm font-mono text-ember">{modelName}</p>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-risk-low animate-pulse" />
          <span className="text-[11px] font-mono text-ink-muted">live</span>
        </div>
      </div>
    </header>
  );
}
