'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'muted' | 'severity-low' | 'severity-medium' | 'severity-high' | 'severity-critical';
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const variants = {
    default: 'bg-primary/20 text-primary border-primary/30',
    secondary: 'bg-slate-700 text-slate-200 border-transparent',
    destructive: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    outline: 'border-border text-foreground',
    muted: 'bg-slate-700/50 text-muted-foreground border-slate-600/50',
    'severity-low': 'severity-low',
    'severity-medium': 'severity-medium',
    'severity-high': 'severity-high',
    'severity-critical': 'severity-critical',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
