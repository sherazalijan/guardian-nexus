"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const TAGS_DATA = [
  { name: "Bot Traffic", value: 400, color: "#ef4444" },
  { name: "Click Injection", value: 300, color: "#f97316" },
  { name: "Device Farm", value: 300, color: "#eab308" },
  { name: "SDK Spoofing", value: 200, color: "#3b82f6" },
  { name: "Install Hijacking", value: 150, color: "#8b5cf6" },
];

export function FraudTagsDonut() {
  return (
    <Card className="bg-white border-slate-200 shadow-sm col-span-1 h-[400px] flex flex-col">
      <CardHeader className="pb-0">
        <CardTitle className="text-slate-800">Fraud Detection by Tags</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col pt-4">
        <div className="flex-1 min-h-0 relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={TAGS_DATA}
                cx="50%"
                cy="50%"
                innerRadius="60%"
                outerRadius="90%"
                paddingAngle={2}
                dataKey="value"
                stroke="none"
              >
                {TAGS_DATA.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                itemStyle={{ color: '#334155' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-3xl font-bold text-slate-800">1,350</span>
            <span className="text-xs text-slate-500 uppercase tracking-wider">Total Tags</span>
          </div>
        </div>
        
        {/* Multi-color legend grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-4 pt-4 border-t border-slate-100">
          {TAGS_DATA.map((tag) => (
            <div key={tag.name} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: tag.color }} />
              <span className="text-xs text-slate-600 font-medium truncate">{tag.name}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
