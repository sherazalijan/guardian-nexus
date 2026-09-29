"use client";

import { Database, AlertTriangle } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useGuardianStore } from "@/store/guardian-store";
import { cn } from "@/lib/utils";

export function ThreatMemory() {
  const matches = useGuardianStore((s) => s.knownThreatMatches);

  if (matches.length === 0) {
    return (
      <Card className="h-full bg-[var(--color-card)]/50">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <Database className="h-4 w-4 text-emerald-500" />
            Threat Memory
          </CardTitle>
          <CardDescription>
            Historical threat pattern matching
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <div className="mb-4 rounded-full bg-emerald-500/10 p-3">
            <Database className="h-6 w-6 text-emerald-500" />
          </div>
          <p className="text-sm font-medium text-[var(--color-foreground)]">
            No known threat matches
          </p>
          <p className="text-xs text-[var(--color-muted-foreground)]">
            Guardian is monitoring for known patterns
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full border-rose-500/20 bg-rose-500/5 shadow-[0_0_15px_rgba(244,63,94,0.05)]">
      <CardHeader className="pb-3 flex flex-row items-start justify-between">
        <div>
          <CardTitle className="flex items-center gap-2 text-rose-500">
            <Database className="h-4 w-4" />
            Threat Memory
          </CardTitle>
          <CardDescription className="text-rose-400/80">
            Historical threat pattern matching
          </CardDescription>
        </div>
        <Badge variant="destructive" className="animate-pulse shadow-md uppercase tracking-widest text-[10px]">
          Known Threat Match
        </Badge>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[250px] pr-4">
          <div className="space-y-4">
            {matches.map((match, i) => (
              <div
                key={i}
                className={cn("rounded-lg border p-4 relative overflow-hidden fade-in", match.occurrence_count === 1 ? "border-amber-500/30 bg-amber-500/10" : "border-rose-500/30 bg-rose-500/10")}
              >
                <div className={cn("absolute top-0 left-0 w-1 h-full", match.occurrence_count === 1 ? "bg-amber-500" : "bg-rose-500")}></div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={cn("h-4 w-4", match.occurrence_count === 1 ? "text-amber-500" : "text-rose-400")} />
                    <span className={cn("text-xs font-bold uppercase tracking-wider", match.occurrence_count === 1 ? "text-amber-500" : "text-rose-400")}>
                      {match.occurrence_count === 1 ? "NEW THREAT PATTERN" : "REPEATED THREAT MATCH"}
                    </span>
                  </div>
                  <Badge variant="destructive" className="font-mono">
                    {Math.round(match.match_score * 100)}% MATCH
                  </Badge>
                </div>
                
                <div className="mb-3">
                  <span className="text-xs text-[var(--color-muted-foreground)] mr-2">
                    Category:
                  </span>
                  <Badge variant="outline" className="border-rose-500/30 text-rose-300 bg-rose-500/10">
                    {match.category.replace(/_/g, " ")}
                  </Badge>
                </div>

                <div className="space-y-1 mb-3">
                  <span className="text-xs text-[var(--color-muted-foreground)]">
                    Matched Indicators:
                  </span>
                  <ul className="list-disc list-inside text-sm text-[var(--color-foreground)] space-y-1 pl-1">
                    {match.matched_indicators.map((indicator, idx) => (
                      <li key={idx} className="text-rose-200/90 text-xs">
                        {indicator.replace(/_/g, " ")}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="flex items-center justify-between mt-4 pt-3 border-t border-rose-500/20">
                  <span className="text-xs font-medium text-rose-400/80">
                    Previously seen {match.occurrence_count} times
                  </span>
                  <span className="text-[10px] font-mono text-rose-500/60 truncate max-w-[120px]">
                    ID: {match.threat_id}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
