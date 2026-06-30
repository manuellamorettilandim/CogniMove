import { Activity, AlertTriangle, Brain, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Kpi } from "@/types";

const icons = {
  purple: Brain,
  green: CheckCircle2,
  red: AlertTriangle,
  yellow: Activity,
  slate: Activity
};

const toneClasses = {
  purple: "bg-violet-50 text-brand",
  green: "bg-emerald-50 text-success",
  red: "bg-red-50 text-danger",
  yellow: "bg-amber-50 text-warning",
  slate: "bg-slate-100 text-slate-700"
};

export function KpiCard({ kpi }: { kpi: Kpi }) {
  const Icon = icons[kpi.tone];

  return (
    <Card className="min-h-32">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-500">{kpi.label}</p>
          <p className="text-3xl font-semibold tracking-tight text-slate-950">{kpi.value}</p>
          <p className="text-xs font-medium text-slate-400">{kpi.trend}</p>
        </div>
        <div className={cn("rounded-2xl p-3", toneClasses[kpi.tone])}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </div>
    </Card>
  );
}
