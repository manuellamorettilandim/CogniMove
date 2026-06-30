"use client";

import { motion } from "framer-motion";
import {
  Command,
  Gamepad2,
  Gauge,
  LayoutDashboard,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { NavItem, PageKey } from "@/types";

export const navItems: NavItem[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "operations", label: "Centro de Operacoes", icon: Command },
  { key: "interactive", label: "Experiencias", icon: Gamepad2 }
];

export function Sidebar({
  activePage,
  onNavigate
}: {
  activePage: PageKey;
  onNavigate: (page: PageKey) => void;
}) {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 bg-slate-950 px-4 py-5 text-white shadow-2xl lg:block">
      <div className="flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand text-white shadow-soft">
          <Gauge className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <p className="text-base font-bold tracking-tight text-white">CogniMove</p>
          <p className="text-xs font-medium text-slate-400">Mobilidade Inteligente</p>
        </div>
      </div>

      <nav className="mt-9 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const selected = activePage === item.key;

          return (
            <button
              key={item.key}
              onClick={() => onNavigate(item.key)}
              className={cn(
                "relative flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-xs font-semibold transition-all",
                selected ? "text-white" : "text-slate-300 hover:bg-white/10 hover:text-white"
              )}
            >
              {selected && (
                <motion.span
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-lg bg-brand"
                  transition={{ type: "spring", stiffness: 380, damping: 32 }}
                />
              )}
              <Icon className="relative h-4 w-4" aria-hidden="true" />
              <span className="relative">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="absolute bottom-4 left-4 right-4 rounded-lg bg-white/8 p-3">
        <p className="text-xs font-semibold text-slate-300">Status do Sistema</p>
        <div className="mt-2 inline-flex rounded-md bg-emerald-500/15 px-2 py-1 text-[11px] font-bold text-emerald-300">
          IA Ativa
        </div>
        <p className="mt-2 text-[11px] text-slate-400">Confianca: 94%</p>
      </div>
    </aside>
  );
}
