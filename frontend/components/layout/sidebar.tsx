"use client";

import { 
  Home, 
  LayoutDashboard, 
  ShieldAlert, 
  Settings, 
  ChevronRight,
  Activity,
  Users,
  PieChart
} from "lucide-react";
import { useState, type ComponentType, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    title: "Home",
    icon: Home,
    items: [
      { title: "Overview", href: "#" },
      { title: "Active Alerts", href: "#" },
    ]
  },
  {
    title: "Dashboards",
    icon: LayoutDashboard,
    items: [
      { title: "Fraud Metrics", href: "#", isActive: true },
      { title: "Traffic Sources", href: "#" },
      { title: "Attribution", href: "#" },
    ]
  },
  {
    title: "Protect360 Analytics",
    icon: ShieldAlert,
    items: [
      { title: "Threat Vectors", href: "#" },
      { title: "Bot Detection", href: "#" },
      { title: "Hijacked Installs", href: "#" },
    ]
  },
  {
    title: "System Settings",
    icon: Settings,
    items: [
      { title: "Thresholds", href: "#" },
      { title: "API Keys", href: "#" },
      { title: "Team", href: "#" },
    ]
  }
];

export const SIDEBAR_CLASS = "bg-[radial-gradient(120%_60%_at_0%_0%,#4338ca_0%,#312e81_45%,#1e1b4b_100%)]";

function SidebarItem({ active, children }: { active?: boolean; children: ReactNode }) {
  return (
    <a href="#" aria-current={active ? "page" : undefined}
       className={`group relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-all duration-200
       ${active ? "bg-white/12 text-white shadow-[inset_0_1px_0_rgb(255_255_255_/_.14)] ring-1 ring-white/10" : "text-indigo-200/80 hover:bg-white/6 hover:text-white"}`}>
      {active && <span className="absolute -left-3 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-indigo-300 shadow-[0_0_12px_2px_rgb(165_180_252_/_.7)]" />}
      <span>{children}</span>
    </a>
  );
}

export function Sidebar() {
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    Dashboards: true,
    "Protect360 Analytics": true
  });

  const toggleGroup = (title: string) => {
    setOpenGroups(prev => ({
      ...prev,
      [title]: !prev[title]
    }));
  };

  return (
    <aside className={cn("w-64 shrink-0 h-screen sticky top-0 text-white flex flex-col border-r border-indigo-900/50 shadow-xl z-20", SIDEBAR_CLASS)}>
      <div className="h-16 flex items-center px-6 border-b border-indigo-800/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <ShieldAlert className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight">Guardian Nexus</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-6 px-4 space-y-6 scrollbar-thin scrollbar-thumb-indigo-700">
        {NAV_ITEMS.map((group) => (
          <div key={group.title} className="space-y-1">
            <button
              onClick={() => toggleGroup(group.title)}
              className="w-full flex items-center justify-between px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-300 hover:text-white transition-colors"
            >
              <div className="flex items-center gap-2">
                <group.icon className="w-4 h-4" />
                {group.title}
              </div>
              <ChevronRight 
                className={cn(
                  "w-3.5 h-3.5 transition-transform duration-200", 
                  openGroups[group.title] && "rotate-90"
                )} 
              />
            </button>
            
            <div className={cn(
              "overflow-hidden transition-all duration-300 ease-in-out",
              openGroups[group.title] ? "max-h-40 opacity-100" : "max-h-0 opacity-0"
            )}>
              <div className="flex flex-col mt-1 space-y-1 pl-6">
                {group.items.map((item) => (
                  <SidebarItem key={item.title} active={item.isActive}>
                    {item.title}
                  </SidebarItem>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-indigo-800/50">
        <div className="bg-indigo-900/50 rounded-lg p-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center justify-center">
            <Users className="w-4 h-4 text-indigo-200" />
          </div>
          <div className="flex flex-col flex-1 min-w-0">
            <span className="text-sm font-medium truncate">NEXUS Admin</span>
            <span className="text-xs text-indigo-300 truncate">Pro Plan</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
