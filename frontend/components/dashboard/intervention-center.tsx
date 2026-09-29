'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useGuardianStore } from '@/store/guardian-store';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface InterventionCenterProps {
  onAcknowledge?: (interventionId: string) => void;
}

function getStatusColor(status: string) {
  switch (status?.toLowerCase()) {
    case 'active': return 'bg-destructive/10 text-destructive border-destructive/20';
    case 'escalated': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
    case 'acknowledged': return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    case 'resolved': return 'bg-green-500/10 text-green-500 border-green-500/20';
    default: return 'bg-muted text-muted-foreground border-border';
  }
}

function getPriorityColor(priority: string) {
  switch (priority?.toLowerCase()) {
    case 'critical': return 'text-destructive';
    case 'high': return 'text-orange-500';
    case 'medium': return 'text-yellow-500';
    default: return 'text-green-500';
  }
}

export function InterventionCenter({ onAcknowledge }: InterventionCenterProps) {
  const interventions = useGuardianStore((s) => s.interventions);
  const interventionAlerts = useGuardianStore((s) => s.interventionAlerts);

  const hasData = interventions.length > 0 || interventionAlerts.length > 0;

  return (
    <Card className="flex flex-col h-full border-destructive/20">
      <CardHeader className="py-3 border-b bg-destructive/5">
        <CardTitle className="flex items-center gap-2 text-base font-semibold text-destructive">
          <AlertTriangle className="w-4 h-4" />
          Intervention Center
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0 relative">
        <div className="h-full max-h-[500px] overflow-y-auto p-4 space-y-4">
          {!hasData ? (
            <div className="flex flex-col items-center justify-center h-40 text-sm text-muted-foreground">
              <CheckCircle2 className="w-8 h-8 opacity-20 mb-2 text-green-500" />
              No active interventions
            </div>
          ) : (
            <>
              {interventions.map((intervention) => (
                <div 
                  key={intervention.intervention_id}
                  className={cn(
                    "p-4 rounded-lg border",
                    intervention.status === 'active' ? "bg-destructive/5 border-destructive/30" : "bg-card"
                  )}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <span className={cn("text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full", getPriorityColor(intervention.priority), "bg-background border")}>
                        {intervention.priority}
                      </span>
                      <span className={cn("text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border", getStatusColor(intervention.status))}>
                        {intervention.status}
                      </span>
                    </div>
                  </div>
                  
                  <h4 className="text-base font-semibold mb-1">{intervention.title}</h4>
                  <p className="text-sm text-muted-foreground mb-4">{intervention.message}</p>
                  
                  {intervention.recommended_action && (
                    <div className="mb-4 p-4 rounded-lg border-2 shadow-md bg-destructive/10 border-destructive animate-pulse duration-[2000ms]">
                      <div className="flex items-center gap-2 mb-2 text-destructive">
                        <AlertTriangle className="w-4 h-4" />
                        <span className="font-extrabold uppercase tracking-wider text-xs">Recommended Action</span>
                      </div>
                      <span className="font-bold text-base text-destructive-foreground">{intervention.recommended_action}</span>
                    </div>
                  )}

                  {intervention.evidence && intervention.evidence.length > 0 && (
                    <div className="mb-4">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 block">Evidence</span>
                      <div className="flex flex-col gap-1">
                        {intervention.evidence.map((ev, i) => (
                          <div key={i} className="text-xs bg-muted p-1.5 rounded">
                            {typeof ev === 'string' ? ev : JSON.stringify(ev)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {intervention.requires_acknowledgement && intervention.status === 'active' && (
                    <div className="flex justify-end mt-4 pt-4 border-t">
                      <Button 
                        variant="destructive" 
                        size="sm"
                        onClick={() => onAcknowledge?.(intervention.intervention_id)}
                      >
                        Acknowledge
                      </Button>
                    </div>
                  )}
                </div>
              ))}

              {interventionAlerts.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">Recent Alerts</h3>
                  <div className="space-y-2">
                    {interventionAlerts.map((alert, i) => (
                      <div key={i} className="p-3 bg-muted/50 rounded-md border text-sm flex gap-3 items-start">
                        <AlertTriangle className={cn("w-4 h-4 shrink-0 mt-0.5", getPriorityColor(alert.level))} />
                        <div>
                          <div className="font-semibold">{alert.title}</div>
                          <div className="text-muted-foreground text-xs mt-1">{alert.message}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
