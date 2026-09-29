'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useGuardianStore } from '@/store/guardian-store';
import { Brain } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

function ConfidenceBar({ confidence }: { confidence: number }) {
  const bars = 10;
  const filledBars = Math.round(confidence * bars);
  
  return (
    <div className="flex gap-[2px]">
      {Array.from({ length: bars }).map((_, i) => (
        <div 
          key={i} 
          className={cn(
            "h-2 w-1.5 rounded-sm",
            i < filledBars ? "bg-primary" : "bg-muted"
          )}
        />
      ))}
    </div>
  );
}

export function VoiceIntelligence() {
  const voiceSignals = useGuardianStore((s) => s.voiceSignals);
  const voicePatterns = useGuardianStore((s) => s.voicePatterns);

  // Group signals by type and take the highest confidence
  const groupedSignals = voiceSignals.reduce((acc, signal) => {
    const existing = acc.get(signal.signal_type);
    if (!existing || existing.confidence < signal.confidence) {
      acc.set(signal.signal_type, signal);
    }
    return acc;
  }, new Map());
  
  const uniqueSignals = Array.from(groupedSignals.values());

  const hasData = uniqueSignals.length > 0 || voicePatterns.length > 0;

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 border-b">
        <CardTitle className="flex items-center gap-2 text-base font-semibold">
          <Brain className="w-4 h-4" />
          Voice Intelligence
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0 relative">
        <div className="h-full max-h-[500px] overflow-y-auto p-4 space-y-6">
          {!hasData ? (
            <div className="flex flex-col items-center justify-center h-40 text-sm text-muted-foreground">
              <Brain className="w-8 h-8 opacity-20 mb-2" />
              No behavioral signals detected
            </div>
          ) : (
            <>
              {uniqueSignals.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Behavioral Signals</h3>
                  <div className="grid gap-2">
                    {uniqueSignals.map((signal, idx) => (
                      <div key={idx} className="flex flex-col p-2 bg-muted/30 rounded-md border text-sm">
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-medium capitalize">{signal.signal_type.replace(/_/g, ' ')}</span>
                          <span className={cn(
                            "text-[10px] uppercase px-1.5 py-0.5 rounded",
                            signal.severity === 'high' || signal.severity === 'critical' ? "bg-destructive/10 text-destructive" :
                            signal.severity === 'medium' ? "bg-orange-500/10 text-orange-500" :
                            "bg-green-500/10 text-green-500"
                          )}>
                            {signal.severity}
                          </span>
                        </div>
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-xs text-muted-foreground">{signal.category}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono">{Math.round(signal.confidence * 100)}%</span>
                            <ConfidenceBar confidence={signal.confidence} />
                          </div>
                        </div>
                        {signal.evidence_text && (
                          <div className="text-xs text-muted-foreground italic border-l-2 pl-2 mt-1">
                            "{signal.evidence_text}"
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {voicePatterns.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Detected Patterns</h3>
                  <div className="grid gap-2">
                    {voicePatterns.map((pattern, idx) => (
                      <div key={idx} className="p-3 bg-secondary/20 rounded-md border text-sm">
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-semibold capitalize text-secondary-foreground">
                            {pattern.pattern_type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs font-mono bg-background px-1 rounded border">
                            {Math.round(pattern.confidence * 100)}%
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground mb-2">
                          Based on: {pattern.signals.join(', ')}
                        </div>
                        {pattern.evidence && pattern.evidence.length > 0 && (
                          <div className="text-xs mt-2 p-2 bg-background/50 rounded border">
                            <ul className="list-disc list-inside">
                              {pattern.evidence.map((ev, i) => (
                                <li key={i}>{typeof ev === 'string' ? ev : JSON.stringify(ev)}</li>
                              ))}
                            </ul>
                          </div>
                        )}
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
