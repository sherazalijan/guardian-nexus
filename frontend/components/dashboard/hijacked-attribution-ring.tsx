"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

const HIJACK_DATA = [
  { name: "Organic (Stolen)", value: 65, color: "#10b981" },
  { name: "Facebook (Stolen)", value: 25, color: "#3b82f6" },
  { name: "Jampp (Stolen)", value: 10, color: "#6366f1" }
];

export function HijackedAttributionRing() {
  return (
    <Card className="bg-white border-slate-200 shadow-sm col-span-1 h-[400px] flex flex-col">
      <CardHeader className="pb-0">
        <CardTitle className="text-slate-800">Hijacked Attribution Corrections</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 pt-4 pb-4">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={HIJACK_DATA}
              cx="50%"
              cy="50%"
              innerRadius="70%"
              outerRadius="90%"
              paddingAngle={5}
              dataKey="value"
              stroke="none"
              cornerRadius={4}
            >
              {HIJACK_DATA.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              itemStyle={{ color: '#334155' }}
              formatter={(value) => [`${value}%`, 'Correction']}
            />
            <Legend 
              verticalAlign="bottom" 
              height={36} 
              iconType="circle"
              wrapperStyle={{ fontSize: '12px' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
