"use client";

import { useEffect, useRef, useState, type MouseEvent } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

/* ============================================================
   KPI CARD (by Claude)
   ============================================================ */
function useCountUp(target: number, ms = 900) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let raf = 0, start: number | null = null;
    const from = 0;
    const tick = (t: number) => {
      start ??= t;
      const p = Math.min((t - start) / ms, 1);
      setV(from + (target - from) * (1 - Math.pow(1 - p, 4)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const w = 120, h = 36, max = Math.max(...data), min = Math.min(...data);
  const pts = data.map((d, i) => [(i / (data.length - 1)) * w, h - 4 - ((d - min) / (max - min || 1)) * (h - 8)]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  const id = `sp-${color.replace("#", "")}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-9 w-full overflow-visible" preserveAspectRatio="none" aria-hidden>
      <defs><linearGradient id={id} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={color} stopOpacity=".25" /><stop offset="1" stopColor={color} stopOpacity="0" /></linearGradient></defs>
      <path d={`${line} L${w} ${h} L0 ${h} Z`} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

type KpiProps = { label: string; value: number; delta: number; series: number[]; suffix?: string; invert?: boolean };

export function KpiCard({ label, value, delta, series, suffix = "", invert = false }: KpiProps) {
  const ref = useRef<HTMLDivElement>(null);
  const shown = useCountUp(value);
  const good = invert ? delta < 0 : delta >= 0;
  const color = good ? "#10b981" : "#e11d48";

  const onMove = (e: MouseEvent) => {
    const r = ref.current!.getBoundingClientRect();
    ref.current!.style.setProperty("--mx", `${e.clientX - r.left}px`);
    ref.current!.style.setProperty("--my", `${e.clientY - r.top}px`);
  };

  return (
    <div ref={ref} onMouseMove={onMove}
      className="group relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition duration-300 hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-[0_1px_2px_rgb(15_23_42/.04),0_8px_24px_-8px_rgb(49_46_129/.18)]">
      {/* cursor spotlight */}
      <div aria-hidden className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
           style={{ background: "radial-gradient(240px circle at var(--mx,50%) var(--my,50%), rgb(99 102 241 / .09), transparent 70%)" }} />
      <div className="relative">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">{label}</p>
          <span className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium tabular-nums ${good ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>
            {delta >= 0 ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}{Math.abs(delta).toFixed(1)}%
          </span>
        </div>
        <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
          {Math.round(shown).toLocaleString()}{suffix}
        </p>
        <div className="mt-3 opacity-80 transition-opacity group-hover:opacity-100"><Sparkline data={series} color={color} /></div>
      </div>
    </div>
  );
}

export function KpiGrid() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 mb-6">
      <KpiCard label="Total Traffic Volume" value={2405119} delta={12.5} series={[3,5,4,7,6,9,8]} />
      <KpiCard label="Fraud Blocked" value={342881} delta={4.2} series={[4,4,6,5,8,7,9]} />
      <KpiCard label="High-Risk IPs" value={4192} delta={-1.8} invert series={[9,8,8,6,7,5,4]} />
      <KpiCard label="Hijacked Attributions" value={89204} delta={15.3} invert series={[2,3,3,5,6,6,8]} />
    </div>
  );
}
