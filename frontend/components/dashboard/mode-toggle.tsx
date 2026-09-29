"use client";

import { Radio, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { SessionMode } from "@/providers/guardian-session-provider";
import { cn } from "@/lib/utils";

export function ModeToggle({
  mode,
  onChange,
  disabled,
}: {
  mode: SessionMode;
  onChange: (mode: SessionMode) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-xl transition-all duration-300">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-bold text-slate-300 uppercase tracking-widest">
          Session Source
        </span>
        <Badge variant={mode === "live" ? "default" : "secondary"} className={cn(mode === "live" ? "bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 border-rose-500/30" : "bg-white/10 text-slate-300 hover:bg-white/20")}>
          {mode === "live" ? "Live" : "Offline"}
        </Badge>
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          variant={mode === "live" ? "default" : "outline"}
          disabled={disabled}
          onClick={() => onChange("live")}
        >
          <Radio className="h-3.5 w-3.5" aria-hidden="true" />
          Live
        </Button>
        <Button
          size="sm"
          variant={mode === "demo" ? "default" : "outline"}
          disabled={disabled}
          onClick={() => onChange("demo")}
        >
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          Demo
        </Button>
      </div>
    </div>
  );
}
