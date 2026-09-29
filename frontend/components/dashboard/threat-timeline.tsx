"use client";

import { List, Info } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { TimelineEvent, ThreatSeverity } from "@/lib/types";
import { formatCategory, severityLabel } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ThreatTimelineProps {
  entries: TimelineEvent[];
}

export function ThreatTimeline({ entries }: ThreatTimelineProps) {
  if (!entries || entries.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <List className="h-4 w-4 text-blue-500" />
            Event Log
          </CardTitle>
          <CardDescription>
            Chronological log of significant session events
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <div className="mb-4 rounded-full bg-[var(--color-card)] p-3 border">
            <List className="h-6 w-6 text-[var(--color-muted-foreground)]" />
          </div>
          <p className="text-sm font-medium text-[var(--color-foreground)]">
            No events recorded
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3 border-b border-[var(--color-border)]">
        <CardTitle className="flex items-center gap-2">
          <List className="h-4 w-4 text-blue-500" />
          Event Log
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[300px] px-4 py-4">
          <div className="space-y-4">
            {entries.map((event, i) => (
              <TimelineEntryItem key={event.event_id || i} event={event} />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function TimelineEntryItem({ event }: { event: TimelineEvent }) {
  const date = new Date(event.timestamp);
  const timeString = date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  });

  return (
    <div className="flex gap-4 p-3 rounded-lg border bg-[var(--color-card)]/50 hover:bg-[var(--color-card)] transition-colors">
      <div className="w-20 shrink-0 text-xs font-mono text-[var(--color-muted-foreground)] pt-0.5">
        {timeString}
      </div>
      
      <div className="flex-1 space-y-1.5">
        <div className="flex items-start justify-between gap-2">
          <span className="text-sm font-semibold text-[var(--color-foreground)] leading-tight">
            {event.label}
          </span>
          {event.severity && (
            <Badge variant={`severity-${event.severity}` as any} className="text-[10px] shrink-0">
              {severityLabel(event.severity)}
            </Badge>
          )}
        </div>
        
        {event.category && (
          <Badge variant="outline" className="text-[10px]">
            {formatCategory(event.category)}
          </Badge>
        )}
        
        {event.detail && (
          <p className="text-xs text-[var(--color-muted-foreground)] flex items-start gap-1.5">
            <Info className="h-3.5 w-3.5 shrink-0 mt-px" />
            {event.detail}
          </p>
        )}
      </div>
    </div>
  );
}
