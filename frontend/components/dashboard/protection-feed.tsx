'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useGuardianStore } from '@/store/guardian-store';
import { ShieldAlert } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ProtectionEvent } from '@/lib/types';

function getEventColor(severity: string) {
  switch (severity?.toLowerCase()) {
    case 'critical': return 'bg-destructive/10 text-destructive border-destructive/20';
    case 'high': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
    case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    default: return 'bg-green-500/10 text-green-500 border-green-500/20';
  }
}

export function ProtectionFeed() {
  const protectionEvents = useGuardianStore((s) => s.protectionEvents);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 border-b sticky top-0 bg-card z-10">
        <CardTitle className="flex items-center gap-2 text-base font-semibold">
          <ShieldAlert className="w-4 h-4" />
          Protection Events
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0 relative">
        <div className="h-full max-h-[500px] overflow-y-auto p-4 space-y-4">
          {protectionEvents.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground italic">
              No protection events
            </div>
          ) : (
            protectionEvents.slice(0, 20).map((event, idx) => (
              <div 
                key={`${event.event_id || event.timestamp}-${idx}`}
                className="p-3 rounded-lg border bg-card shadow-sm animate-in slide-in-from-right-4 fade-in duration-300"
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <span className={cn("text-[10px] px-1.5 py-0.5 rounded-sm font-semibold uppercase tracking-wider border", getEventColor(event.severity))}>
                      {event.severity}
                    </span>
                    <span className="text-xs font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded-sm">
                      {event.event_type}
                    </span>
                  </div>
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                
                <h4 className="text-sm font-semibold mb-1">{event.title || event.event_type}</h4>
                <p className="text-sm text-muted-foreground mb-3">{event.message}</p>
                
                {event.recommended_action && (
                  <div className="mt-2 text-xs p-2 bg-primary/5 rounded border border-primary/10">
                    <span className="font-semibold text-primary mr-1">Action:</span>
                    {event.recommended_action}
                  </div>
                )}
                
                {event.evidence && event.evidence.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {event.evidence.map((ev, i) => (
                      <span key={i} className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded">
                        {typeof ev === 'string' ? ev : JSON.stringify(ev)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
