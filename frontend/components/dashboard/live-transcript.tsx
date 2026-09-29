'use client';

import React, { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { useGuardianStore } from '@/store/guardian-store';
import { MessageSquare } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export function LiveTranscript() {
  const transcripts = useGuardianStore((s) => s.transcripts);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [transcripts]);

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="py-3 border-b">
        <CardTitle className="flex items-center gap-2 text-base font-semibold">
          <MessageSquare className="w-4 h-4" />
          Live Transcript
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0 relative">
        <div 
          ref={scrollRef}
          className="h-full max-h-[400px] overflow-y-auto p-4 space-y-3"
        >
          {transcripts.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground italic">
              Waiting for speech...
            </div>
          ) : (
            transcripts.map((t, idx) => {
              const isRecent = idx >= transcripts.length - 3;
              return (
                <div 
                  key={idx} 
                  className={cn(
                    "p-2 rounded-md border-l-2 transition-all duration-500",
                    t.is_final 
                      ? "border-l-primary bg-background text-foreground" 
                      : "border-l-muted bg-muted/20 text-muted-foreground italic",
                    !isRecent && t.is_final && "opacity-40 hover:opacity-100"
                  )}
                >
                  <div className="flex justify-between items-start gap-2">
                    <span className="text-sm">
                      {t.text}
                    </span>
                    {!t.is_final ? (
                      <span className="text-[10px] uppercase tracking-wider text-muted-foreground shrink-0 border px-1 rounded bg-muted/30">
                        Interim
                      </span>
                    ) : (
                      t.confidence && t.confidence >= 0.5 && (
                        <span className="text-[10px] shrink-0 text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">
                          {Math.round(t.confidence * 100)}%
                        </span>
                      )
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
