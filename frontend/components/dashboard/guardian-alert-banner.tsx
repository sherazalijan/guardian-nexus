'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useGuardianStore } from '@/store/guardian-store';
import { ShieldAlert, AlertCircle, Info, Shield } from 'lucide-react';

function getAlertConfig(level: string) {
  switch (level?.toLowerCase()) {
    case 'critical': 
      return {
        bg: 'bg-rose-500',
        text: 'text-rose-50',
        border: 'border-rose-600',
        icon: AlertCircle,
        pulse: true
      };
    case 'high_risk': 
      return {
        bg: 'bg-orange-500',
        text: 'text-orange-50',
        border: 'border-orange-600',
        icon: ShieldAlert,
        pulse: false
      };
    case 'warning': 
      return {
        bg: 'bg-amber-500',
        text: 'text-amber-950',
        border: 'border-amber-600',
        icon: AlertCircle,
        pulse: false
      };
    default: 
      return {
        bg: 'bg-blue-500',
        text: 'text-blue-50',
        border: 'border-blue-600',
        icon: Info,
        pulse: false
      };
  }
}

export function GuardianAlertBanner() {
  const guardianAlerts = useGuardianStore((s) => s.guardianAlerts);
  
  if (!guardianAlerts || guardianAlerts.length === 0) {
    return null;
  }

  // Find the first active alert to display prominently
  const activeAlert = guardianAlerts.find(a => a.status === 'active');
  const inactiveAlerts = guardianAlerts.filter(a => a.status !== 'active');

  if (!activeAlert && inactiveAlerts.length === 0) {
    return null;
  }

  return (
    <div className="w-full space-y-2 mb-4">
      {activeAlert && (
        <div className="w-full">
          {(() => {
            const config = getAlertConfig(activeAlert.level);
            const Icon = config.icon;
            
            return (
              <div 
                className={cn(
                  "w-full p-4 rounded-lg border-2 shadow-lg flex items-start gap-4 transition-all",
                  config.bg,
                  config.text,
                  config.border,
                  config.pulse && "animate-pulse shadow-rose-500/50"
                )}
              >
                <div className="shrink-0 p-2 bg-white/20 rounded-full">
                  <Icon className="w-8 h-8" />
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <h3 className="text-xl font-bold uppercase tracking-wide">
                      {activeAlert.title}
                    </h3>
                    <div className="flex gap-2">
                      <span className="text-xs font-mono bg-black/20 px-2 py-1 rounded">
                        RISK: {activeAlert.risk_score}
                      </span>
                      {activeAlert.confidence && (
                        <span className="text-xs font-mono bg-black/20 px-2 py-1 rounded">
                          CONF: {Math.round(activeAlert.confidence * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="mt-1 text-base font-medium opacity-90">
                    {activeAlert.message}
                  </p>
                  <div className="mt-3 text-xs opacity-75 flex gap-4">
                    <span>{new Date(activeAlert.timestamp).toLocaleTimeString()}</span>
                    <span className="uppercase">{activeAlert.level.replace(/_/g, ' ')}</span>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {inactiveAlerts.length > 0 && (
        <div className="flex flex-col gap-2">
          {inactiveAlerts.slice(0, 3).map((alert, idx) => {
            const config = getAlertConfig(alert.level);
            return (
              <div 
                key={idx}
                className={cn(
                  "w-full p-2 px-4 rounded-md border text-sm flex items-center justify-between opacity-70",
                  "bg-muted text-muted-foreground"
                )}
              >
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  <span className="font-semibold">{alert.title}</span>
                  <span className="mx-2 opacity-50">|</span>
                  <span className="truncate max-w-[500px]">{alert.message}</span>
                </div>
                <div className="text-xs">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
