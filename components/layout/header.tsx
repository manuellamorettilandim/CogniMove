"use client";

import { Badge } from "@/components/ui/badge";
import { useClock } from "@/hooks/use-clock";

export function Header({ title }: { title: string }) {
  const { date, time } = useClock();

  return (
    <header className="sticky top-0 z-20 -mx-4 border-b border-slate-200/80 bg-canvas/90 px-4 py-4 backdrop-blur-xl sm:-mx-8 sm:px-8 lg:mx-0 lg:px-0">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-950 sm:text-2xl">{title}</h1>
          <p className="text-xs font-medium text-slate-500">Centro de operacoes para mobilidade urbana inteligente</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge>
            <span className="h-2 w-2 rounded-full bg-success" />
            Sistema Online
          </Badge>
          <div className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600">
            {date}
          </div>
          <div className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-950">
            {time}
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-950 text-sm font-bold text-white">
            CM
          </div>
        </div>
      </div>
    </header>
  );
}
