"use client";

import { Mic, MicOff, Play, Square, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useGuardianStore } from "@/store/guardian-store";
import type { ConnectionStatus } from "@/lib/types";

interface LiveAudioPanelProps {
  onStart: () => void;
  onStop: () => void;
  isBusy: boolean;
}

export function LiveAudioPanel({ onStart, onStop, isBusy }: LiveAudioPanelProps) {
  const connectionStatus = useGuardianStore((s) => s.connectionStatus);
  const micStatus = useGuardianStore((s) => s.micStatus);
  const isActive = connectionStatus === "connected";
  const isConnecting = connectionStatus === "connecting" || connectionStatus === "reconnecting";

  return (
    <div
      className={cn(
        "rounded-xl transition-all duration-300",
        isActive && "shadow-lg shadow-emerald-500/5 ring-1 ring-emerald-500/30"
      )}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">
          Session Control
        </h2>
        <MicIndicator micStatus={micStatus} />
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          {!isActive && !isConnecting ? (
            <button
              onClick={onStart}
              disabled={isBusy}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 rounded-lg px-5 py-2.5",
                "text-sm font-bold transition-all duration-200",
                "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "active:scale-[0.98]"
              )}
              aria-label="Start Guardian session"
            >
              {isBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Play className="h-4 w-4" aria-hidden="true" />
              )}
              {isBusy ? "Starting…" : "Start Session"}
            </button>
          ) : (
            <button
              onClick={onStop}
              disabled={isBusy}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 rounded-lg px-5 py-2.5",
                "text-sm font-bold transition-all duration-200",
                "bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-500/20",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "active:scale-[0.98]"
              )}
              aria-label="End Guardian session"
            >
              <Square className="h-4 w-4" aria-hidden="true" />
              End Session
            </button>
          )}
        </div>

        {isConnecting && (
          <div className="flex items-center gap-2 text-amber-400 text-xs font-medium px-1">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            <span>{connectionStatus === "reconnecting" ? "Reconnecting…" : "Connecting…"}</span>
          </div>
        )}
        
        {connectionStatus === "error" && (
          <div className="flex items-center gap-2 text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-md p-2 text-xs font-medium mt-1">
            <span className="font-bold">Backend Offline:</span> Check if server is running on localhost:8000
          </div>
        )}
      </div>
    </div>
  );
}

function MicIndicator({ micStatus }: { micStatus: string }) {
  if (micStatus === "active") {
    return (
      <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-medium">
        <Mic className="h-3.5 w-3.5 animate-pulse" aria-hidden="true" />
        <span>Mic active</span>
      </div>
    );
  }
  if (micStatus === "denied") {
    return (
      <div className="flex items-center gap-1.5 text-rose-400 text-xs font-medium">
        <MicOff className="h-3.5 w-3.5" aria-hidden="true" />
        <span>Mic denied</span>
      </div>
    );
  }
  if (micStatus === "requesting") {
    return (
      <div className="flex items-center gap-1.5 text-amber-400 text-xs font-medium">
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        <span>Requesting mic…</span>
      </div>
    );
  }
  return null;
}
