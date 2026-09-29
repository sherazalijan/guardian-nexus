'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useGuardianStore } from '@/store/guardian-store';
import { Shield } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { RiskResult } from '@/lib/types';

function getRiskColorClass(score: number) {
  if (score >= 80) return "text-destructive stroke-destructive";
  if (score >= 60) return "text-orange-500 stroke-orange-500";
  if (score >= 30) return "text-yellow-500 stroke-yellow-500";
  return "text-green-500 stroke-green-500";
}

function getRiskBgClass(score: number) {
  if (score >= 80) return "bg-destructive/10 text-destructive";
  if (score >= 60) return "bg-orange-500/10 text-orange-500";
  if (score >= 30) return "bg-yellow-500/10 text-yellow-500";
  return "bg-green-500/10 text-green-500";
}

export function RiskDisplay() {
  const latestRisk = useGuardianStore((s) => s.latestRisk);

  if (!latestRisk) {
    return (
      <Card className="h-full">
        <CardHeader className="py-3 border-b">
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <Shield className="w-4 h-4" />
            Risk Assessment
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-48 text-sm text-muted-foreground">
          <div className="flex flex-col items-center gap-2">
            <Shield className="w-8 h-8 opacity-20" />
            No risk assessment yet
          </div>
        </CardContent>
      </Card>
    );
  }

  const {
    score: risk_score,
    severity,
    evidence_state,
    explanation,
    risk_factors: factors = [],
    recommended_action
  } = latestRisk;

  const colorClass = getRiskColorClass(risk_score);
  const bgClass = getRiskBgClass(risk_score);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="py-3 border-b">
        <CardTitle className="flex justify-between items-center text-base font-semibold">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Risk Assessment
          </div>
          <span className={cn("text-xs px-2 py-1 rounded-full uppercase tracking-wider font-bold", bgClass)}>
            {severity}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-4 space-y-6 overflow-y-auto max-h-[500px]">
        <div className="flex justify-center">
          <div className="relative w-32 h-32 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
              <circle
                className="stroke-muted fill-none transition-all duration-1000"
                strokeWidth="8"
                cx="50"
                cy="50"
                r="40"
              />
              <circle
                className={cn("fill-none transition-all duration-1000 ease-out", colorClass)}
                strokeWidth="8"
                strokeDasharray={251.2}
                strokeDashoffset={251.2 - (251.2 * risk_score) / 100}
                strokeLinecap="round"
                cx="50"
                cy="50"
                r="40"
              />
            </svg>
            <div className="absolute flex flex-col items-center justify-center">
              <span className={cn("text-3xl font-bold transition-colors", colorClass.split(' ')[0])}>
                {Math.round(risk_score)}
              </span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-widest">
                Score
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex gap-2 text-sm">
            <span className="font-semibold text-muted-foreground w-24">Evidence:</span>
            <span className="capitalize">{evidence_state?.replace(/_/g, ' ')}</span>
          </div>
          <div className="text-sm bg-muted/30 p-3 rounded-md">
            {explanation}
          </div>
        </div>

        {factors.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold mb-2">Risk Factors</h4>
            {factors.map((factor, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span>{factor.name}</span>
                  <span className="text-muted-foreground">{Math.round(factor.contribution * 100)}%</span>
                </div>
                <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                  <div 
                    className={cn("h-full rounded-full", getRiskColorClass(factor.contribution * 100).split(' ')[0].replace('text-', 'bg-'))}
                    style={{ width: `${factor.contribution * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {recommended_action && (
          <div className={cn("mt-4 p-4 border-2 rounded-md shadow-md animate-pulse duration-[3000ms]", bgClass, bgClass.replace('bg-', 'border-').replace('/10', '/40'))}>
            <h4 className="flex items-center gap-2 text-sm font-extrabold mb-2 uppercase tracking-wider">
              <Shield className="w-4 h-4" />
              Recommended Action
            </h4>
            <p className="text-base font-semibold">{recommended_action}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
