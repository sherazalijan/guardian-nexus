"use client";

import { ShieldAlert, AlertTriangle, ShieldCheck, Activity } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { RiskResult, ThreatSeverity } from "@/lib/types";
import { severityLabel } from "@/lib/types";
import { cn } from "@/lib/utils";

interface RiskAlertPanelProps {
  risk: RiskResult | null;
}

export function RiskAlertPanel({ risk }: RiskAlertPanelProps) {
  if (!risk) {
    return (
      <Card className="h-full bg-[var(--color-card)]/50">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-[var(--color-muted-foreground)]">
            <ShieldCheck className="h-4 w-4" />
            Threat Assessment
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <div className="mb-4 rounded-full bg-[var(--color-card)] border p-4">
            <Activity className="h-8 w-8 text-[var(--color-muted-foreground)]/50 animate-pulse" />
          </div>
          <p className="text-sm font-medium text-[var(--color-muted-foreground)]">
            Waiting for analysis…
          </p>
        </CardContent>
      </Card>
    );
  }

  const isCritical = risk.severity === "critical";
  const isHigh = risk.severity === "high";
  const isWarning = isCritical || isHigh;

  return (
    <Card className={cn(
      "h-full transition-all duration-500 overflow-hidden",
      isCritical ? "border-rose-500/50 shadow-[0_0_30px_rgba(244,63,94,0.15)]" :
      isHigh ? "border-orange-500/40 shadow-[0_0_20px_rgba(249,115,22,0.1)]" :
      ""
    )}>
      <CardHeader className={cn(
        "pb-4 border-b",
        isCritical ? "bg-rose-500/10 border-rose-500/20" :
        isHigh ? "bg-orange-500/10 border-orange-500/20" :
        "border-[var(--color-border)] bg-[var(--color-card)]"
      )}>
        <div className="flex items-start justify-between">
          <CardTitle className={cn(
            "flex items-center gap-2",
            isCritical ? "text-rose-500" :
            isHigh ? "text-orange-500" :
            "text-[var(--color-foreground)]"
          )}>
            <ShieldAlert className={cn(
              "h-5 w-5",
              isCritical && "animate-pulse"
            )} />
            Threat Assessment
          </CardTitle>
          <Badge variant={`severity-${risk.severity}` as any} className="px-3 py-1 text-xs">
            {severityLabel(risk.severity)}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="p-6">
        <div className="flex flex-col items-center mb-6">
          <div className="relative mb-2">
            <svg width="120" height="120" viewBox="0 0 120 120" className="transform -rotate-90">
              <circle cx="60" cy="60" r="54" fill="none" stroke="var(--color-border)" strokeWidth="8" />
              <circle 
                cx="60" 
                cy="60" 
                r="54" 
                fill="none" 
                stroke={
                  risk.severity === "critical" ? "var(--color-severity-critical)" :
                  risk.severity === "high" ? "var(--color-severity-high)" :
                  risk.severity === "medium" ? "var(--color-severity-medium)" :
                  "var(--color-severity-low)"
                }
                strokeWidth="8" 
                strokeDasharray="339.292" 
                strokeDashoffset={339.292 - (339.292 * risk.score) / 100}
                className="transition-all duration-1000 ease-out"
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={cn(
                "text-4xl font-black font-mono tracking-tighter",
                risk.severity === "critical" ? "text-rose-500" :
                risk.severity === "high" ? "text-orange-500" :
                risk.severity === "medium" ? "text-amber-500" :
                "text-emerald-500"
              )}>
                {risk.score}
              </span>
            </div>
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-muted-foreground)]">
            Risk Score
          </span>
        </div>

        <div className="space-y-6">
          <div>
            <h4 className="text-sm font-semibold mb-2">Assessment</h4>
            <p className="text-sm text-[var(--color-muted-foreground)] leading-relaxed">
              {risk.explanation}
            </p>
          </div>

          {risk.risk_factors.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-muted-foreground)] mb-3">
                Risk Factors
              </h4>
              <div className="space-y-3">
                {risk.risk_factors.map((factor, idx) => (
                  <div key={idx} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-[var(--color-foreground)] truncate pr-2">
                        {factor.name.replace(/_/g, " ")}
                      </span>
                      <span className="text-[var(--color-muted-foreground)] font-mono shrink-0">
                        {Math.round(factor.contribution * 100)}%
                      </span>
                    </div>
                    <Progress value={factor.contribution * 100} severity={risk.severity} className="h-1.5" />
                    <p className="text-[10px] text-[var(--color-muted-foreground)] truncate">
                      {factor.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={cn(
            "mt-4 p-3 rounded-lg border",
            isWarning ? "bg-rose-500/10 border-rose-500/20" : "bg-[var(--color-card)] border-[var(--color-border)]"
          )}>
            <div className="flex items-start gap-2">
              <AlertTriangle className={cn(
                "h-4 w-4 mt-0.5",
                isWarning ? "text-rose-400" : "text-amber-400"
              )} />
              <div>
                <span className={cn(
                  "block text-xs font-bold uppercase tracking-wider mb-1",
                  isWarning ? "text-rose-400" : "text-amber-400"
                )}>
                  Recommended Action: {risk.recommended_action}
                </span>
                <span className="text-xs text-[var(--color-muted-foreground)]">
                  Evidence level: <span className="font-semibold text-[var(--color-foreground)]">{risk.evidence_state}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
