"use client";

import { ShieldAlert } from "lucide-react";
import { useGuardianStore } from "@/store/guardian-store";

export function ScamAlertBanner() {
  const score = useGuardianStore((s: any) => s.riskAssessment?.score ?? 0);
  const interventions = useGuardianStore((s: any) => s.interventions ?? []);

  // Only show if score is high
  if (score < 70) return null;

  const latestIntervention = interventions.length > 0 ? interventions[interventions.length - 1] : null;
  const reason = latestIntervention?.reason || "The caller is using known pressure and impersonation patterns.";
  const caller = "Unknown"; // In a real app, this could come from call metadata

  return (
    <div role="alert" className="relative overflow-hidden rounded-2xl border border-rose-200 bg-rose-50 shadow-[0_8px_30px_-12px_rgb(225_29_72_/_.45)] mb-6 mx-auto max-w-7xl w-full">
      <div aria-hidden className="h-1.5 w-full nx-stripes bg-[length:40px_100%]"
           style={{ backgroundImage: "repeating-linear-gradient(-45deg,#e11d48 0 10px,#fb7185 10px 20px)" }} />
      <div className="flex items-center gap-4 px-5 py-4">
        <span className="relative grid size-11 shrink-0 place-items-center rounded-full bg-rose-600 text-white">
          <span className="absolute inset-0 animate-ping rounded-full bg-rose-500/40" />
          <ShieldAlert className="relative size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-rose-900">Scam attempt detected</p>
          <p className="truncate text-sm text-rose-800/80">{reason}{caller !== "Unknown" ? ` Caller: ${caller}` : ""}</p>
        </div>
        <button className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-rose-700 active:scale-[.98] focus-visible:ring-2 focus-visible:ring-rose-400 focus-visible:ring-offset-2">
          Review intervention
        </button>
      </div>
    </div>
  );
}
