"use client";

import { useEffect, useState } from "react";
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldOff,
  Wifi,
  WifiOff,
  Loader2,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  ConnectionStatus,
  {
    label: string;
    sublabel: string;
    icon: typeof Shield;
    className: string;
    pulseClass: string;
  }
> = {
  idle: {
    label: "GUARDIAN STANDBY",
    sublabel: "Ready to protect",
    icon: Shield,
    className: "text-slate-400",
    pulseClass: "",
  },
  connecting: {
    label: "GUARDIAN CONNECTING",
    sublabel: "Establishing secure connection…",
    icon: Loader2,
    className: "text-blue-400",
    pulseClass: "animate-spin",
  },
  connected: {
    label: "GUARDIAN ACTIVE",
    sublabel: "Monitoring live interaction",
    icon: ShieldCheck,
    className: "text-emerald-400",
    pulseClass: "animate-pulse",
  },
  reconnecting: {
    label: "GUARDIAN RECONNECTING",
    sublabel: "Connection interrupted — reconnecting…",
    icon: Loader2,
    className: "text-amber-400",
    pulseClass: "animate-spin",
  },
  disconnected: {
    label: "GUARDIAN OFFLINE",
    sublabel: "Session ended",
    icon: ShieldOff,
    className: "text-slate-500",
    pulseClass: "",
  },
  error: {
    label: "GUARDIAN ERROR",
    sublabel: "Connection failed",
    icon: ShieldAlert,
    className: "text-rose-400",
    pulseClass: "",
  },
};

interface DashboardHeaderProps {
  connectionStatus: ConnectionStatus;
  sessionStartedAt?: number | null;
}

export function DashboardHeader({
  connectionStatus,
  sessionStartedAt,
}: DashboardHeaderProps) {
  const config = STATUS_CONFIG[connectionStatus];
  const Icon = config.icon;

  return (
    <header
      className={cn(
        "sticky top-0 z-50 border-b backdrop-blur-xl",
        "bg-[var(--background)]/80 border-[var(--border)]"
      )}
    >
      <div className="flex items-center justify-between px-4 py-3 sm:px-6">
        {/* Brand + Status */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg",
                "bg-blue-500/10 border border-blue-500/20"
              )}
            >
              <Shield className="h-5 w-5 text-blue-400" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-[var(--foreground)]">
                Guardian Nexus
              </h1>
              <p className="text-[11px] font-medium tracking-wider text-[var(--muted-foreground)] uppercase">
                Digital Protection System
              </p>
            </div>
          </div>

          <div className="hidden sm:block h-8 w-px bg-[var(--border)]" />

          {/* Connection status */}
          <div className="hidden sm:flex items-center gap-2.5">
            <div className="relative">
              <Icon
                className={cn("h-5 w-5", config.className, config.pulseClass)}
                aria-hidden="true"
              />
              {connectionStatus === "connected" && (
                <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              )}
            </div>
            <div>
              <p
                className={cn(
                  "text-xs font-bold tracking-wider uppercase",
                  config.className
                )}
              >
                {config.label}
              </p>
              <p className="text-[10px] text-[var(--muted-foreground)]">
                {config.sublabel}
              </p>
            </div>
          </div>
        </div>

        {/* Right side: Session timer + connection indicator */}
        <div className="flex items-center gap-3">
          {sessionStartedAt && connectionStatus === "connected" && (
            <SessionTimer startedAt={sessionStartedAt} />
          )}
          <div
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1.5",
              "text-xs font-medium border",
              connectionStatus === "connected"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                : connectionStatus === "error"
                  ? "border-rose-500/30 bg-rose-500/10 text-rose-400"
                  : connectionStatus === "connecting" ||
                      connectionStatus === "reconnecting"
                    ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
                    : "border-slate-500/30 bg-slate-500/10 text-slate-400"
            )}
            role="status"
            aria-label={`Connection status: ${config.label}`}
          >
            {connectionStatus === "connected" ? (
              <Wifi className="h-3 w-3" aria-hidden="true" />
            ) : (
              <WifiOff className="h-3 w-3" aria-hidden="true" />
            )}
            <span className="hidden xs:inline">
              {connectionStatus === "connected"
                ? "Connected"
                : connectionStatus === "connecting"
                  ? "Connecting…"
                  : connectionStatus === "reconnecting"
                    ? "Reconnecting…"
                    : connectionStatus === "error"
                      ? "Error"
                      : "Offline"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

function SessionTimer({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [startedAt]);

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded-full px-3 py-1.5",
        "text-xs font-mono font-medium",
        "border border-blue-500/20 bg-blue-500/5 text-blue-300"
      )}
      aria-label={`Session duration: ${minutes} minutes ${seconds} seconds`}
    >
      <Clock className="h-3 w-3" aria-hidden="true" />
      <span>
        {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
      </span>
    </div>
  );
}
