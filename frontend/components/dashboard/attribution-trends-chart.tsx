"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipProps } from "recharts";

type Series = { key: string; label: string; color: string };
type ChartProps = { data: Record<string, number | string>[]; xKey: string; series: Series[] };

function GlassTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="min-w-40 rounded-xl border border-white/70 bg-white/85 p-3 shadow-[0_1px_2px_rgb(15_23_42/.04),0_8px_24px_-8px_rgb(49_46_129/.18)] backdrop-blur-md">
      <p className="mb-1.5 text-xs font-medium text-slate-500">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey as string} className="flex items-center justify-between gap-6 text-sm">
          <span className="flex items-center gap-2 text-slate-600"><span className="size-2 rounded-full" style={{ background: p.color, boxShadow: `0 0 8px ${p.color}` }} />{p.name}</span>
          <span className="font-semibold tabular-nums text-slate-900">{Number(p.value).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function GlowTrendChart({ data, xKey, series }: ChartProps) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <defs>
            {series.map((s) => (
              <linearGradient key={s.key} id={`fill-${s.key}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={s.color} stopOpacity={0.28} />
                <stop offset="100%" stopColor={s.color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid vertical={false} stroke="#e2e8f0" strokeDasharray="3 6" />
          <XAxis dataKey={xKey} tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} dy={8} />
          <YAxis tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} />
          <Tooltip content={<GlassTooltip />} cursor={{ stroke: "#6366f1", strokeOpacity: 0.35, strokeDasharray: "4 4" }} />
          {series.map((s) => (
            <Area key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2.5}
                  fill={`url(#fill-${s.key})`} dot={false}
                  activeDot={{ r: 5, strokeWidth: 3, stroke: "#fff", fill: s.color }}
                  style={{ filter: `drop-shadow(0 4px 8px ${s.color}55)` }}
                  animationDuration={1100} animationEasing="ease-out" />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const demoTrend = ["Oct 1","Oct 2","Oct 3","Oct 4","Oct 5","Oct 6","Oct 7"].map((d, i) => ({
  day: d, organic: 4000 + i * 400 + (i % 2) * 600, paid: 2500 + i * 250, hijacked: 600 + ((i * 370) % 900),
}));

export function AttributionTrendsChart() {
  return (
    <div className="rounded-3xl border border-slate-200/80 bg-white p-6 shadow-sm col-span-1 h-[400px] flex flex-col">
      <h2 className="mb-2 text-sm font-semibold text-slate-900">Attribution Trend</h2>
      <div className="flex-1">
        <GlowTrendChart data={demoTrend} xKey="day" series={[
          { key: "organic", label: "Organic", color: "#4f46e5" },
          { key: "paid", label: "Paid", color: "#10b981" },
          { key: "hijacked", label: "Hijacked", color: "#e11d48" },
        ]} />
      </div>
    </div>
  );
}
