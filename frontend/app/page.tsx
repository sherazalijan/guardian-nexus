"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { TopHeader } from "@/components/layout/top-header";
import { ScamAlertBanner } from "@/components/dashboard/scam-alert-banner";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { LiveSentinel } from "@/components/dashboard/live-sentinel";
import { PipelineStrip } from "@/components/dashboard/pipeline-strip";
import { FraudMediaSources } from "@/components/dashboard/fraud-media-sources";
import { AttributionTrendsChart } from "@/components/dashboard/attribution-trends-chart";
import { FraudTagsDonut } from "@/components/dashboard/fraud-tags-donut";
import { HijackedAttributionRing } from "@/components/dashboard/hijacked-attribution-ring";
import { useGuardianSession } from "@/providers/guardian-session-provider";
import { ModeToggle } from "@/components/dashboard/mode-toggle";
import { LiveAudioPanel } from "@/components/dashboard/live-audio-panel";

export default function DashboardPage() {
  const { mode, setMode, startSession, stopSession, isBusy } = useGuardianSession();
  return (
    <div className="nx-canvas flex min-h-screen text-slate-900 font-sans selection:bg-indigo-500/30">
      <Sidebar />
      
      <div className="flex flex-col flex-1 min-w-0 h-screen overflow-y-auto relative">
        <TopHeader />
        
        <main className="flex-1 p-6 relative">
          <div className="max-w-7xl mx-auto flex flex-col">
            
            <ScamAlertBanner />
            <KpiGrid />
            
            <div className="grid gap-6 lg:grid-cols-4 mb-6">
              <div className="lg:col-span-1 space-y-6">
                <div className="rounded-3xl border border-slate-200/80 bg-slate-900 p-6 shadow-sm">
                  <ModeToggle mode={mode} onChange={setMode} disabled={isBusy} />
                </div>
                <div className="rounded-3xl border border-slate-200/80 bg-slate-900 p-6 shadow-sm">
                  <LiveAudioPanel onStart={startSession} onStop={stopSession} isBusy={isBusy} />
                </div>
              </div>
              
              <div className="lg:col-span-3 grid gap-6 lg:grid-cols-[380px_1fr]">
                <LiveSentinel />
                <AttributionTrendsChart />
              </div>
            </div>
            
            {/* 2x2 Grid of remaining visualizations */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
              <FraudMediaSources />
              <FraudTagsDonut />
              <HijackedAttributionRing />
            </div>
            
            <PipelineStrip />
          </div>
        </main>
        
        {/* Branding Footer */}
        <footer className="py-4 border-t border-slate-200 bg-white/70 backdrop-blur-sm text-center sticky bottom-0">
          <p className="text-sm text-slate-500 font-medium">
            Dashboard Architecture & Fraud Logic by sheraz al jan, Founder, NEXUS
          </p>
        </footer>
      </div>
    </div>
  );
}
