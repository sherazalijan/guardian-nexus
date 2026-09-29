"use client";

import { Clock, Info } from "lucide-react";
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
import type { ThreatSeverity } from "@/lib/types";
import { formatCategory, severityLabel } from "@/lib/types";

export function SessionTimeline() {
  const events = useGuardianStore((s) => s.timelineEvents);

  if (events.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-blue-500" />
            Session Timeline
          </CardTitle>
          <CardDescription>
            Chronological log of session events
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <div className="mb-4 rounded-full bg-blue-500/10 p-3">
            <Clock className="h-6 w-6 text-blue-500" />
          </div>
          <p className="text-sm font-medium text-[var(--color-foreground)]">
            Timeline will appear as the session progresses
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3 border-b border-[var(--color-border)]">
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-blue-500" />
          Session Timeline
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[250px] px-4 py-4">
          <div className="relative border-l-2 border-[var(--color-border)] ml-3 pl-5 space-y-6">
            {events.map((event, i) => (
              <TimelineItem key={event.event_id || i} event={event} />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function TimelineItem({ event }: { event: any }) {
  const date = new Date(event.timestamp);
  const timeString = date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  });

  const severityColor = getSeverityColor(event.severity);
  const severityBg = getSeverityBg(event.severity);

  return (
    <div className="relative fade-in">
      <div 
        className={cn(
          "absolute -left-[1.6rem] h-4 w-4 rounded-full border-2 border-[var(--color-background)] mt-0.5",
          severityBg
        )}
      />
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-medium text-[var(--color-muted-foreground)]">
            {timeString}
          </span>
          {event.severity && (
            <Badge variant={`severity-${event.severity}` as any} className="text-[10px]">
              {severityLabel(event.severity as ThreatSeverity)}
            </Badge>
          )}
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-[var(--color-foreground)]">
            {event.label}
          </span>
          {event.category && (
            <Badge variant="outline" className="w-fit text-[10px]">
              {formatCategory(event.category)}
            </Badge>
          )}
          {event.detail && (
            <p className="text-xs text-[var(--color-muted-foreground)] flex items-start gap-1 mt-1">
              <Info className="h-3 w-3 mt-0.5 shrink-0" />
              {event.detail}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function getSeverityColor(severity: string | null) {
  switch (severity) {
    case "critical": return "text-rose-500";
    case "high": return "text-orange-500";
    case "medium": return "text-amber-500";
    case "low": return "text-emerald-500";
    default: return "text-blue-500";
  }
}

function getSeverityBg(severity: string | null) {
  switch (severity) {
    case "critical": return "bg-rose-500";
    case "high": return "bg-orange-500";
    case "medium": return "bg-amber-500";
    case "low": return "bg-emerald-500";
    default: return "bg-blue-500";
  }
}
