"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

const SOURCES_DATA = [
  { name: "facebook_ads", total: 450120, fraud: 154000, clean: 296120, fraudPct: 34.2 },
  { name: "jampp_int", total: 320500, fraud: 198000, clean: 122500, fraudPct: 61.7 },
  { name: "googleadwords_int", total: 280000, fraud: 45000, clean: 235000, fraudPct: 16.0 },
  { name: "applovin_int", total: 150000, fraud: 82000, clean: 68000, fraudPct: 54.6 },
  { name: "mintegral_int", total: 95000, fraud: 65000, clean: 30000, fraudPct: 68.4 }
];

export function FraudMediaSources() {
  return (
    <Card className="bg-white border-slate-200 shadow-sm col-span-1 h-[400px] flex flex-col">
      <CardHeader className="pb-2 border-b border-slate-100">
        <CardTitle className="text-slate-800 flex items-center justify-between">
          <span>Top Fraudulent Media Sources</span>
          <span className="text-xs text-slate-400 font-normal normal-case">By absolute volume</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto pt-4 space-y-6 scrollbar-thin scrollbar-thumb-slate-200">
        {SOURCES_DATA.map((source) => (
          <div key={source.name} className="space-y-2">
            <div className="flex justify-between items-end text-sm">
              <span className="font-semibold text-slate-700">{source.name}</span>
              <div className="flex gap-4 text-xs font-medium">
                <span className="text-red-600">{source.fraud.toLocaleString()} Fraud ({source.fraudPct}%)</span>
                <span className="text-emerald-600">{source.clean.toLocaleString()} Clean</span>
              </div>
            </div>
            {/* Stacked Progress Bar */}
            <div className="h-3 w-full bg-slate-100 rounded-full flex overflow-hidden">
              <div 
                className="h-full bg-red-500 transition-all duration-1000" 
                style={{ width: `${source.fraudPct}%` }}
                title="Fraudulent Traffic"
              />
              <div 
                className="h-full bg-emerald-500 transition-all duration-1000" 
                style={{ width: `${100 - source.fraudPct}%` }}
                title="Clean Traffic"
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
