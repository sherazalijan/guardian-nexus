'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { ThreatSeverity } from '@/lib/types';

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  severity?: ThreatSeverity;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, severity, ...props }, ref) => {
    
    let colorClass = 'bg-blue-600';
    if (severity === 'low') colorClass = 'bg-emerald-500';
    else if (severity === 'medium') colorClass = 'bg-amber-500';
    else if (severity === 'high') colorClass = 'bg-orange-500';
    else if (severity === 'critical') colorClass = 'bg-rose-500';

    return (
      <div
        ref={ref}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        className={cn('relative h-2 w-full rounded-full bg-slate-800 overflow-hidden', className)}
        {...props}
      >
        <div
          className={cn('h-full rounded-full transition-all duration-500 ease-out flex-1', colorClass)}
          style={{ width: `${Math.min(100, Math.max(0, value || 0))}%` }}
        />
      </div>
    );
  }
);
Progress.displayName = 'Progress';

export { Progress };
