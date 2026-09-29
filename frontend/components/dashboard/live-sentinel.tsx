"use client";

import { useMemo } from "react";
import { Mic, ShieldAlert, ShieldCheck, WifiOff } from "lucide-react";
import { useGuardianStore } from "@/store/guardian-store";

/* AssemblyAI attribution */
export function AssemblyAIBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M4 12v0M8 8v8M12 4v16M16 8v8M20 12v0" /></svg>
      Powered by AssemblyAI
    </span>
  );
}

const BARS = 32;

function tone(score: number) {
  if (score >= 70) return { name: "Critical", hex: "#e11d48", soft: "bg-rose-50 text-rose-700 ring-rose-200", Icon: ShieldAlert };
  if (score >= 35) return { name: "Elevated", hex: "#f59e0b", soft: "bg-amber-50 text-amber-700 ring-amber-200", Icon: ShieldAlert };
  return { name: "Clear", hex: "#10b981", soft: "bg-emerald-50 text-emerald-700 ring-emerald-200", Icon: ShieldCheck };
}

export function LiveSentinel() {
  const status = useGuardianStore((s: any) => s.connectionStatus);
  const score: number = useGuardianStore((s: any) => s.riskAssessment?.score ?? 0);
  const transcripts = useGuardianStore((s: any) => s.transcripts ?? []);

  const live = status === "connected";
  const t = tone(score);
  const last = transcripts[transcripts.length - 1];
  const lastText: string = typeof last === "string" ? last : last?.text ?? "";

  // Gauge geometry: 270° arc
  const R = 78, C = 2 * Math.PI * R, ARC = C * 0.75;
  const offset = ARC - (ARC * Math.min(Math.max(score, 0), 100)) / 100;

  const bars = useMemo(() => Array.from({ length: BARS }, (_, i) => ({
    delay: `${((i * 97) % 700) / 1000}s`,
    dur: `${0.9 + ((i * 53) % 60) / 100}s`,
  })), []);

  return (
    <section className="relative overflow-hidden rounded-3xl border border-white/70 bg-white/80 p-6 shadow-[0_1px_2px_rgb(15_23_42/.04),0_8px_24px_-8px_rgb(49_46_129/.18)] backdrop-blur-xl">
      {/* ambient glow follows risk tone */}
      <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full blur-3xl transition-colors duration-700"
           style={{ background: `${t.hex}22` }} />

      <header className="relative flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Live call risk</h2>
          <p className="text-xs text-slate-500">{live ? "Live transcript by AssemblyAI" : "Start a session to begin monitoring"}</p>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${live ? t.soft : "bg-slate-100 text-slate-500 ring-slate-200"}`}>
          {live ? <span className="relative flex size-2"><span className="absolute inset-0 animate-ping rounded-full opacity-60" style={{ background: t.hex }} /><span className="relative size-2 rounded-full" style={{ background: t.hex }} /></span> : <WifiOff className="size-3" />}
          {live ? t.name : status === "connecting" ? "Connecting" : "Offline"}
        </span>
      </header>

      <div className="relative mx-auto mt-2 grid size-56 place-items-center">
        <svg viewBox="0 0 200 200" className="absolute inset-0 -rotate-[225deg]">
          <defs>
            <filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="4" /></filter>
          </defs>
          <circle cx="100" cy="100" r={R} fill="none" stroke="#e2e8f0" strokeWidth="12" strokeLinecap="round" strokeDasharray={`${ARC} ${C}`} />
          {/* glow copy */}
          <circle cx="100" cy="100" r={R} fill="none" stroke={t.hex} strokeWidth="12" strokeLinecap="round" opacity=".45" filter="url(#glow)"
                  strokeDasharray={`${ARC} ${C}`} strokeDashoffset={offset} style={{ transition: "stroke-dashoffset 900ms cubic-bezier(.22,1,.36,1), stroke 500ms" }} />
          <circle cx="100" cy="100" r={R} fill="none" stroke={t.hex} strokeWidth="12" strokeLinecap="round"
                  strokeDasharray={`${ARC} ${C}`} strokeDashoffset={offset} style={{ transition: "stroke-dashoffset 900ms cubic-bezier(.22,1,.36,1), stroke 500ms" }} />
        </svg>

        {/* radar sweep while listening */}
        {live && (
          <div aria-hidden className="absolute inset-6 nx-sweep rounded-full opacity-60"
               style={{ background: `conic-gradient(from 0deg, transparent 0 78%, ${t.hex}33 100%)`, maskImage: "radial-gradient(circle, transparent 58%, #000 60%)" }} />
        )}

        <div className="relative text-center">
          <div className="text-5xl font-semibold tabular-nums tracking-tight text-slate-900">{Math.round(score)}</div>
          <div className="mt-0.5 text-xs text-slate-500">out of 100</div>
        </div>
      </div>

      {/* live waveform */}
      <div aria-hidden className="mx-auto flex h-10 max-w-sm items-center justify-center gap-[3px]">
        {bars.map((b, i) => (
          <span key={i} className={`h-full w-[3px] origin-center rounded-full ${live ? "nx-wave" : "scale-y-[.12]"}`}
                style={{ background: live ? t.hex : "#cbd5e1", opacity: live ? 0.85 : 1, animationDelay: b.delay, animationDuration: b.dur, transition: "background 500ms" }} />
        ))}
      </div>

      {/* latest transcript */}
      <div className="relative mt-4 flex items-start gap-3 rounded-2xl bg-slate-50/80 p-3 ring-1 ring-slate-200/70 shadow-[inset_0_1px_0_rgb(255_255_255/.9)]">
        <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-white text-slate-500 shadow-sm ring-1 ring-slate-200"><Mic className="size-3.5" /></span>
        <p key={lastText} className="line-clamp-2 min-h-[2.5rem] text-sm leading-5 text-slate-700 nx-fade">
          {lastText || <span className="text-slate-400">Transcript will appear here as the caller speaks.</span>}
        </p>
      </div>
      <div className="relative mt-3"><AssemblyAIBadge /></div>
    </section>
  );
}
