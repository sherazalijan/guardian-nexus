"use client";

import { FileText, ShieldAlert, AlertTriangle, ShieldCheck, Clock, Activity, Target } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useGuardianStore } from "@/store/guardian-store";
import { formatCategory, severityLabel } from "@/lib/types";
import { cn } from "@/lib/utils";

export function SessionSummary() {
  const summary = useGuardianStore((s) => s.sessionSummary);

  if (!summary) return null;

  const durationStr = summary.duration_seconds 
    ? `${Math.floor(summary.duration_seconds / 60)}m ${summary.duration_seconds % 60}s`
    : "Unknown";

  const isSafe = summary.highest_severity === "low" || summary.final_risk_score < 25;

  return (
    <div className="fade-in mt-4">
      <Card className={cn(
        "border-2 overflow-hidden",
        isSafe ? "border-emerald-500/50" : "border-rose-500/50"
      )}>
        <div className={cn(
          "px-6 py-4 flex items-center gap-3 border-b",
          isSafe ? "bg-emerald-500/10 border-emerald-500/20" : "bg-rose-500/10 border-rose-500/20"
        )}>
          {isSafe ? (
            <ShieldCheck className="h-6 w-6 text-emerald-500" />
          ) : (
            <ShieldAlert className="h-6 w-6 text-rose-500" />
          )}
          <div>
            <CardTitle className="text-lg">Session Summary</CardTitle>
            <p className={cn(
              "text-xs font-medium uppercase tracking-wider",
              isSafe ? "text-emerald-400" : "text-rose-400"
            )}>
              {isSafe ? "Session concluded safely" : "Threats detected during session"}
            </p>
          </div>
        </div>

        <CardContent className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Key Metrics */}
          <div className="space-y-4 col-span-1 lg:col-span-1 border-b md:border-b-0 md:border-r border-[var(--color-border)] pb-4 md:pb-0 pr-0 md:pr-4">
            <div>
              <span className="text-xs text-[var(--color-muted-foreground)] uppercase tracking-wider font-semibold">
                Final Assessment
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className={cn(
                  "text-4xl font-bold font-mono tracking-tighter",
                  isSafe ? "text-emerald-500" : "text-rose-500"
                )}>
                  {summary.final_risk_score}
                </span>
                <span className="text-sm text-[var(--color-muted-foreground)]">/ 100</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge variant={`severity-${summary.highest_severity}` as any}>
                  Peak: {severityLabel(summary.highest_severity)}
                </Badge>
                {summary.highest_risk_score !== summary.final_risk_score && (
                  <Badge variant="outline" className="text-xs">
                    Max: {summary.highest_risk_score}
                  </Badge>
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-[var(--color-border)]">
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--color-muted-foreground)] flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" /> Duration
                </span>
                <span className="font-mono font-medium">{durationStr}</span>
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="col-span-1 lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <span className="text-xs text-[var(--color-muted-foreground)] uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-2">
                  <Target className="h-3.5 w-3.5" /> Detected Categories
                </span>
                <div className="flex flex-wrap gap-2">
                  {summary.detected_categories.length > 0 ? (
                    summary.detected_categories.map(c => (
                      <Badge key={c} variant="outline" className="bg-[var(--color-card)]">
                        {formatCategory(c)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-[var(--color-muted-foreground)]">None</span>
                  )}
                </div>
              </div>

              <div>
                <span className="text-xs text-[var(--color-muted-foreground)] uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-2">
                  <Activity className="h-3.5 w-3.5" /> Session Stats
                </span>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-[var(--color-card)] rounded-md p-2 border border-[var(--color-border)] text-center">
                    <div className="text-amber-500 font-bold text-lg">{summary.warning_count}</div>
                    <div className="text-[10px] text-[var(--color-muted-foreground)] uppercase">Warnings</div>
                  </div>
                  <div className="bg-[var(--color-card)] rounded-md p-2 border border-[var(--color-border)] text-center">
                    <div className="text-rose-500 font-bold text-lg">{summary.critical_alert_count}</div>
                    <div className="text-[10px] text-[var(--color-muted-foreground)] uppercase">Alerts</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
               <div>
                <span className="text-xs text-[var(--color-muted-foreground)] uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-2">
                  <AlertTriangle className="h-3.5 w-3.5" /> Final Recommendation
                </span>
                <div className={cn(
                  "p-3 rounded-lg border text-sm font-medium",
                  isSafe 
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-100" 
                    : "bg-rose-500/10 border-rose-500/20 text-rose-100"
                )}>
                  {summary.recommended_final_action}
                </div>
              </div>

              {summary.detected_signals && summary.detected_signals.length > 0 && (
                <div>
                  <span className="text-xs text-[var(--color-muted-foreground)] uppercase tracking-wider font-semibold mb-2 block">
                    Key Signals
                  </span>
                  <ul className="text-xs space-y-1 text-[var(--color-muted-foreground)] pl-4 list-disc">
                    {summary.detected_signals.slice(0, 4).map(s => (
                      <li key={s}>{formatCategory(s)}</li>
                    ))}
                    {summary.detected_signals.length > 4 && (
                      <li className="list-none text-[10px] italic pt-1">
                        + {summary.detected_signals.length - 4} more
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>

        </CardContent>
      </Card>
    </div>
  );
}
