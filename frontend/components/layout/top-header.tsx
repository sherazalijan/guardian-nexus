"use client";

import { Bell, Search, ShieldCheck } from "lucide-react";
import { useGuardianStore } from "@/store/guardian-store";

export const HEADER_CLASS =
  "sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200/60 bg-white/70 px-6 backdrop-blur-xl backdrop-saturate-150 supports-[backdrop-filter]:bg-white/60";

export const SELECT_CLASS =
  "h-9 rounded-lg border border-slate-200 bg-white/80 px-3 text-sm text-slate-700 shadow-[inset_0_1px_0_rgb(255_255_255/.9)] outline-none transition hover:border-indigo-300 focus-visible:ring-2 focus-visible:ring-indigo-400/50";

export function SearchBar() {
  return (
    <label className="group relative ml-auto hidden w-72 md:block">
      <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400 transition group-focus-within:text-indigo-500" />
      <input placeholder="Search calls, numbers, tags" className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50/80 pl-9 pr-3 text-sm outline-none transition focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-500/10" />
    </label>
  );
}

export function NotificationBell({ count = 0 }: { count?: number }) {
  return (
    <button aria-label="Notifications" className="relative grid size-9 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-indigo-400/50">
      <Bell className="size-[18px]" />
      {count > 0 && <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-rose-500 ring-2 ring-white" />}
    </button>
  );
}

export function TopHeader() {
  const score = useGuardianStore((s: any) => s.riskAssessment?.score ?? 0);
  
  return (
    <header className={HEADER_CLASS}>
      <h1 className="text-xl font-bold text-slate-800 tracking-tight mr-4">Fraud Analytics</h1>
      
      <select className={SELECT_CLASS}>
        <option>All regions</option>
        <option>North America</option>
        <option>EMEA</option>
        <option>APAC</option>
      </select>
      
      <select className={SELECT_CLASS}>
        <option>Last 7 days</option>
        <option>Last 30 days</option>
        <option>Today</option>
      </select>
      
      <SearchBar />
      
      <div className="flex items-center gap-2 ml-4">
        {/* Protection Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-xs font-semibold border border-green-200">
          <ShieldCheck className="w-4 h-4" />
          <span className="hidden sm:inline">Active Protection</span>
        </div>
        
        <NotificationBell count={score >= 70 ? 1 : 0} />
      </div>
    </header>
  );
}
