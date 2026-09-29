'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useGuardianStore } from '@/store/guardian-store';
import { FileSearch } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { EvidenceItem } from '@/lib/types';

function getSeverityColor(severity: string) {
  switch (severity?.toLowerCase()) {
    case 'critical': return 'text-destructive bg-destructive/10';
    case 'high': return 'text-orange-500 bg-orange-500/10';
    case 'medium': return 'text-yellow-500 bg-yellow-500/10';
    default: return 'text-green-500 bg-green-500/10';
  }
}

export function EvidencePanel() {
  const evidenceItems = useGuardianStore((s) => s.evidenceItems);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 border-b">
        <CardTitle className="flex items-center gap-2 text-base font-semibold">
          <FileSearch className="w-4 h-4" />
          Evidence Log
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0 relative">
        <div className="h-full max-h-[500px] overflow-y-auto p-4 space-y-3">
          {evidenceItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-sm text-muted-foreground">
              <FileSearch className="w-8 h-8 opacity-20 mb-2" />
              No evidence collected
            </div>
          ) : (
            evidenceItems.map((item, idx) => (
              <div 
                key={idx}
                className="relative p-3 rounded-md border bg-card overflow-hidden font-mono text-sm"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-border" />
                <div className="flex justify-between items-start mb-2 pl-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-muted">
                      {item.signal}
                    </span>
                    <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground">
                      {item.category}
                    </span>
                    <span className={cn("text-[10px] uppercase px-1.5 py-0.5 rounded", getSeverityColor(item.severity))}>
                      {item.severity}
                    </span>
                  </div>
                </div>
                
                <div className="pl-2 mt-2 mb-2 text-muted-foreground">
                  "{item.text}"
                </div>

                <div className="pl-2 flex gap-4 text-xs mt-3 pt-2 border-t border-border/50">
                  {item.confidence !== undefined && (
                    <div className="flex items-center gap-1">
                      <span className="text-muted-foreground">CONF:</span>
                      <span className="font-semibold">{Math.round(item.confidence * 100)}%</span>
                    </div>
                  )}
                  {item.risk_score !== undefined && (
                    <div className="flex items-center gap-1">
                      <span className="text-muted-foreground">RISK:</span>
                      <span className="font-semibold text-destructive">{Math.round(item.risk_score)}</span>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
