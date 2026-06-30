"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useForm } from "react-hook-form";
import {
  ArrowRight,
  Bike,
  Bus,
  Camera,
  Car,
  CheckCircle2,
  CloudSun,
  DollarSign,
  Footprints,
  Hospital,
  Lightbulb,
  MapPin,
  Play,
  Radar,
  RotateCcw,
  School,
  ShieldAlert,
  ShieldCheck,
  TrafficCone,
  TrendingDown,
  Upload,
  Video,
  Wallet,
  X,
  Zap
} from "lucide-react";
import { BarChartCard } from "@/components/charts/bar-chart-card";
import { HeatmapCard } from "@/components/charts/heatmap-card";
import { LineChartCard } from "@/components/charts/line-chart-card";
import { PieChartCard } from "@/components/charts/pie-chart-card";
import { Header } from "@/components/layout/header";
import { navItems, Sidebar } from "@/components/layout/sidebar";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, SelectField } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  cityScenarios,
  flowData,
  heatmapData,
  monitoringStats,
  operationPoints,
  smartCityInvestments,
  violationData
} from "@/mock/traffic-data";
import type { DiagnosisResult, OperationPoint, PageKey } from "@/types";

type ScenarioForm = {
  cidade: string;
  clima: string;
  horario: string;
  fluxo: string;
  dia: string;
};

const pageTitles: Record<PageKey, string> = {
  dashboard: "Monitoramento Inteligente de Transito",
  monitoring: "Monitoramento",
  diagnosis: "Analise Inteligente de Risco",
  reports: "Relatorios",
  scenarios: "Cenarios Urbanos",
  operations: "Centro de Operacoes",
  interactive: "Experiencias Interativas",
  about: "Sobre o CogniMove",
  settings: "Configuracoes"
};

export default function Home() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [booting, setBooting] = useState(true);

  if (booting) {
    return <OpeningLoader onComplete={() => setBooting(false)} />;
  }

  return (
    <div className="min-h-screen bg-canvas">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <MobileNav activePage={activePage} onNavigate={setActivePage} />
      <main className="px-4 pb-10 pt-20 sm:px-8 lg:ml-64 lg:px-6 lg:pt-0">
        <Header title={pageTitles[activePage]} />
        <AnimatePresence mode="wait">
          <motion.section
            key={activePage}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.22 }}
            className="mx-auto mt-8 max-w-7xl"
          >
            {activePage === "dashboard" && <DashboardPage />}
            {activePage === "monitoring" && <MonitoringPage />}
            {activePage === "diagnosis" && <DiagnosisPage />}
            {activePage === "reports" && <ReportsPage />}
            {activePage === "scenarios" && <ScenariosPage />}
            {activePage === "operations" && <OperationsCenterPage />}
            {activePage === "interactive" && <InteractivePage />}
            {activePage === "about" && <AboutPage />}
            {activePage === "settings" && <SettingsPage />}
          </motion.section>
        </AnimatePresence>
      </main>
    </div>
  );
}

function MobileNav({
  activePage,
  onNavigate
}: {
  activePage: PageKey;
  onNavigate: (page: PageKey) => void;
}) {
  return (
    <div className="fixed inset-x-0 top-0 z-40 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
      <SelectField value={activePage} onChange={(event) => onNavigate(event.target.value as PageKey)}>
        {navItems.map((item) => (
          <option key={item.key} value={item.key}>
            {item.label}
          </option>
        ))}
      </SelectField>
    </div>
  );
}

function OpeningLoader({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const progressTimer = window.setInterval(() => {
      setProgress((current) => Math.min(current + 4, 100));
    }, 140);
    const doneTimer = window.setTimeout(onComplete, 3900);

    return () => {
      window.clearInterval(progressTimer);
      window.clearTimeout(doneTimer);
    };
  }, [onComplete]);

  return (
    <motion.div
      className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 text-white"
      exit={{ opacity: 0 }}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,rgba(109,40,217,0.32),transparent_38%),linear-gradient(180deg,#020617_0%,#0f172a_100%)]" />
      <motion.div
        className="absolute inset-x-0 top-20 h-px bg-brand-light/50"
        animate={{ opacity: [0.2, 0.8, 0.2], x: ["-20%", "20%", "-20%"] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative z-10 grid w-full max-w-6xl gap-10 px-6 lg:grid-cols-[1.25fr_0.75fr] lg:items-center">
        <SmartCityScene />
        <div className="space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 2.1, duration: 0.55 }}
          >
            <div className="inline-flex items-center gap-3 rounded-2xl border border-white/10 bg-white/8 px-4 py-3 backdrop-blur">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand">
                <Radar className="h-6 w-6" />
              </div>
              <div>
                <p className="text-2xl font-extrabold tracking-tight">CogniMove</p>
                <p className="text-xs font-semibold text-violet-200">Monitoramento Inteligente para Smart Cities</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 2.45, duration: 0.5 }}
            className="space-y-3"
          >
            <p className="text-sm font-medium text-slate-300">
              As imagens estao sendo analisadas pela Inteligencia Artificial...
            </p>
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-brand to-emerald-400"
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.18 }}
              />
            </div>
            <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
              <span>YOLO + OpenCV mock pipeline</span>
              <span>{progress}%</span>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

function SmartCityScene() {
  const buildings = [
    { height: "h-36", width: "w-16", delay: 0.1 },
    { height: "h-52", width: "w-20", delay: 0.2 },
    { height: "h-44", width: "w-14", delay: 0.3 },
    { height: "h-60", width: "w-24", delay: 0.4 },
    { height: "h-40", width: "w-16", delay: 0.5 }
  ];

  return (
    <div className="relative h-[520px] overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.03] p-8 shadow-2xl">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(139,92,246,0.08)_1px,transparent_1px),linear-gradient(0deg,rgba(139,92,246,0.08)_1px,transparent_1px)] bg-[size:42px_42px]" />
      <motion.div
        className="absolute left-16 right-16 top-20 h-40 rounded-full border border-violet-400/30"
        animate={{ scale: [0.95, 1.04, 0.95], opacity: [0.2, 0.65, 0.2] }}
        transition={{ duration: 2.6, repeat: Infinity }}
      />

      <div className="absolute bottom-28 left-8 right-8 flex items-end justify-center gap-4">
        {buildings.map((building, index) => (
          <motion.div
            key={index}
            initial={{ y: 90, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: building.delay, duration: 0.65, ease: "easeOut" }}
            className={`${building.height} ${building.width} rounded-t-2xl border border-white/10 bg-slate-800/90 p-2`}
          >
            <div className="grid grid-cols-2 gap-1">
              {Array.from({ length: 10 }).map((_, windowIndex) => (
                <motion.span
                  key={windowIndex}
                  className="h-2 rounded-sm bg-violet-300/60"
                  animate={{ opacity: [0.25, 0.9, 0.25] }}
                  transition={{ delay: windowIndex * 0.08, duration: 2, repeat: Infinity }}
                />
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-32 bg-slate-900">
        <div className="absolute left-1/2 top-0 h-full w-28 -translate-x-1/2 bg-slate-800 [clip-path:polygon(42%_0,58%_0,100%_100%,0_100%)]" />
        <div className="absolute left-1/2 top-2 h-full w-1 -translate-x-1/2 bg-white/30" />
        <div className="absolute left-0 right-0 top-10 h-3 bg-white/10" />
      </div>

      <motion.div className="absolute bottom-16 left-10" animate={{ x: [0, 430] }} transition={{ duration: 3.2, repeat: Infinity, ease: "linear" }}>
        <Car className="h-8 w-8 text-emerald-300" />
        <DetectionBox delay={2.2} color="border-emerald-400" label="carro" />
      </motion.div>
      <motion.div className="absolute bottom-9 right-16" animate={{ x: [0, -360] }} transition={{ duration: 3.8, repeat: Infinity, ease: "linear" }}>
        <Bike className="h-7 w-7 text-amber-300" />
        <DetectionBox delay={2.45} color="border-amber-300" label="moto" />
      </motion.div>
      <motion.div className="absolute bottom-24 left-28" animate={{ x: [0, 220] }} transition={{ duration: 4.1, repeat: Infinity, ease: "linear" }}>
        <Bus className="h-9 w-9 text-violet-300" />
        <DetectionBox delay={2.65} color="border-violet-300" label="onibus" />
      </motion.div>

      <motion.div className="absolute bottom-24 right-24" animate={{ x: [0, -80, 0] }} transition={{ duration: 3, repeat: Infinity }}>
        <Footprints className="h-8 w-8 text-slate-200" />
        <DetectionBox delay={2.75} color="border-sky-300" label="pedestre" />
      </motion.div>

      <div className="absolute bottom-28 left-20 h-20 w-7 rounded-t-lg bg-slate-700">
        <span className="mx-auto mt-2 block h-3 w-3 rounded-full bg-red-500" />
        <span className="mx-auto mt-1 block h-3 w-3 rounded-full bg-amber-400" />
        <span className="mx-auto mt-1 block h-3 w-3 rounded-full bg-emerald-400" />
      </div>
      <div className="absolute bottom-32 right-20 rounded-full bg-slate-800 p-3 text-violet-200">
        <Video className="h-6 w-6" />
        <DetectionBox delay={2.9} color="border-violet-300" label="camera" />
      </div>
      <motion.div
        className="absolute bottom-44 right-28 h-px w-80 origin-right bg-gradient-to-l from-violet-300 to-transparent"
        animate={{ opacity: [0.2, 1, 0.2], rotate: [-8, 6, -8] }}
        transition={{ duration: 2.4, repeat: Infinity }}
      />
    </div>
  );
}

function DetectionBox({ delay, color, label }: { delay: number; color: string; label: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.86 }}
      animate={{ opacity: [0, 1, 1], scale: 1 }}
      transition={{ delay, duration: 0.5 }}
      className={`absolute -inset-2 rounded-lg border-2 ${color}`}
    >
      <span className="absolute -top-5 left-0 rounded bg-slate-950/80 px-1.5 py-0.5 text-[10px] font-bold text-white">
        {label}
      </span>
    </motion.div>
  );
}

function UrbanCameraFeed({ className = "" }: { className?: string }) {
  return (
    <div className={`relative overflow-hidden bg-slate-900 ${className}`}>
      <div className="absolute inset-0 bg-[linear-gradient(180deg,#475569_0%,#94a3b8_38%,#1e293b_38%,#0f172a_100%)]" />
      <div className="absolute inset-x-0 top-0 h-1/2 bg-[linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px)] bg-[size:54px_100%]" />
      <div className="absolute bottom-[38%] left-0 right-0 flex items-end justify-center gap-3">
        {[42, 70, 54, 86, 48, 64, 38].map((height, index) => (
          <div key={index} className="w-12 rounded-t-lg border border-white/10 bg-slate-700/90 p-1" style={{ height }}>
            <div className="grid grid-cols-2 gap-1">
              {Array.from({ length: 6 }).map((_, windowIndex) => (
                <span key={windowIndex} className="h-1 rounded-sm bg-violet-200/60" />
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="absolute bottom-0 left-1/2 h-[62%] w-[74%] -translate-x-1/2 bg-slate-800 [clip-path:polygon(39%_0,61%_0,100%_100%,0_100%)]" />
      <div className="absolute bottom-0 left-1/2 h-[60%] w-px -translate-x-1/2 bg-white/50" />
      <div className="absolute bottom-[18%] left-[22%] h-[18%] w-[18%] rounded-t-xl bg-slate-950 shadow-lg">
        <span className="absolute -top-2 left-3 right-3 h-3 rounded-t-lg bg-red-500" />
        <span className="absolute bottom-1 left-2 h-2 w-3 rounded-full bg-amber-200" />
        <span className="absolute bottom-1 right-2 h-2 w-3 rounded-full bg-amber-200" />
      </div>
      <div className="absolute bottom-[23%] right-[24%] h-[13%] w-[15%] rounded-t-xl bg-brand shadow-lg">
        <span className="absolute -top-1 left-3 right-3 h-2 rounded-t-lg bg-violet-300" />
        <span className="absolute bottom-1 left-2 h-1.5 w-2.5 rounded-full bg-amber-200" />
        <span className="absolute bottom-1 right-2 h-1.5 w-2.5 rounded-full bg-amber-200" />
      </div>
      <div className="absolute bottom-[30%] left-[47%] h-[17%] w-[8%] rounded-t-lg bg-emerald-400 shadow-lg" />
      <div className="absolute bottom-[23%] right-[12%] h-[24%] w-[7%] rounded-full bg-slate-950">
        <span className="mx-auto mt-2 block h-3 w-3 rounded-full bg-red-500" />
        <span className="mx-auto mt-1 block h-3 w-3 rounded-full bg-amber-400" />
        <span className="mx-auto mt-1 block h-3 w-3 rounded-full bg-emerald-400" />
      </div>
      <div className="absolute bottom-[17%] right-[36%] h-[22%] w-[8%]">
        <span className="mx-auto block h-4 w-4 rounded-full bg-slate-100" />
        <span className="mx-auto mt-1 block h-9 w-3 rounded-full bg-amber-300" />
      </div>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,transparent_0%,rgba(15,23,42,0.24)_72%)]" />
    </div>
  );
}

function CityPointIllustration({ point }: { point: OperationPoint }) {
  return (
    <div className="relative mt-5 h-48 w-full overflow-hidden rounded-2xl bg-slate-100">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(100,116,139,0.18)_1px,transparent_1px),linear-gradient(0deg,rgba(100,116,139,0.18)_1px,transparent_1px)] bg-[size:38px_38px]" />
      <div className="absolute left-[12%] top-[18%] h-[72%] w-8 -rotate-12 rounded-full bg-white shadow-sm" />
      <div className="absolute left-[4%] right-[8%] top-[48%] h-8 rounded-full bg-white shadow-sm" />
      <div className="absolute bottom-4 right-5 h-20 w-28 rounded-2xl bg-emerald-100" />
      <div className={`absolute left-1/2 top-1/2 flex h-16 w-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-2xl border-4 border-white text-white shadow-soft ${riskBackground(point.risk)}`}>
        {point.id === "school-zone" && <School className="h-7 w-7" />}
        {point.id === "hospital" && <Hospital className="h-7 w-7" />}
        {point.id === "main-avenue" && <Car className="h-7 w-7" />}
        {point.id === "central-crossing" && <TrafficCone className="h-7 w-7" />}
      </div>
      <div className="absolute bottom-4 left-4 rounded-xl bg-white/90 px-3 py-2 shadow-sm">
        <p className="text-xs font-bold text-slate-500">Ponto selecionado</p>
        <p className="text-sm font-extrabold text-slate-950">{point.name}</p>
      </div>
    </div>
  );
}

function DashboardPage() {
  const [activeDashboardTab, setActiveDashboardTab] = useState<"vision" | "diagnosis" | "report">("vision");
  const tabs = [
    { id: "vision", label: "Monitoramento" },
    { id: "diagnosis", label: "Diagnostico" },
    { id: "report", label: "Relatorio" }
  ] as const;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-panel lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-bold text-brand">Centro Inteligente de Operacoes</p>
          <h2 className="mt-1 text-2xl font-extrabold tracking-tight text-slate-950">
            Monitoramento urbano por IA
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Visao limpa para acompanhar video, diagnostico, indicadores e recomendacoes simuladas.
          </p>
        </div>
        <div className="grid rounded-xl border border-slate-200 bg-slate-50 p-1 sm:grid-cols-3">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveDashboardTab(tab.id)}
              className={`rounded-lg px-4 py-2 text-xs font-bold transition ${
                activeDashboardTab === tab.id ? "bg-brand text-white shadow-soft" : "text-slate-500 hover:text-slate-950"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeDashboardTab}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {activeDashboardTab === "vision" && (
            <div className="grid gap-4 xl:grid-cols-[1.5fr_0.65fr]">
              <LiveMonitoringPanel />
              <AiSummary />
            </div>
          )}
          {activeDashboardTab === "diagnosis" && (
            <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
              <RootCausePanel />
              <Card className="space-y-4">
                <CardTitle>Recomendacoes Operacionais</CardTitle>
                {[
                  "Priorizar semaforo inteligente no cruzamento central.",
                  "Ativar fiscalizacao de velocidade entre 17h e 19h.",
                  "Reforcar travessia protegida em zona escolar."
                ].map((item) => (
                  <div key={item} className="flex gap-3 rounded-xl bg-slate-50 p-4 text-sm font-semibold text-slate-700">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none text-success" />
                    {item}
                  </div>
                ))}
              </Card>
            </div>
          )}
          {activeDashboardTab === "report" && <ManagementReportPanel />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function LiveMonitoringPanel() {
  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold text-brand">1. Monitoramento em Tempo Real (Visao da IA)</p>
        </div>
        <span className="rounded-full bg-red-950 px-2 py-1 text-[10px] font-bold text-white">REC</span>
      </div>
      <div className="relative min-h-[390px] overflow-hidden rounded-xl bg-slate-900">
        <UrbanCameraFeed className="absolute inset-0 opacity-95" />
        <div className="absolute left-[34%] top-[37%] rounded-md border-2 border-red-500 bg-red-500/85 px-2 py-1 text-[11px] font-bold text-white">
          Infracao: Avanco de Sinal<br />Confianca: 96%
        </div>
        <div className="absolute right-[15%] top-[19%] rounded-md border-2 border-emerald-500 bg-emerald-500/85 px-2 py-1 text-[11px] font-bold text-white">
          Semaforo: Vermelho<br />Confianca: 99%
        </div>
        <div className="absolute bottom-[19%] right-[12%] rounded-md border-2 border-amber-400 bg-amber-300/90 px-2 py-1 text-[11px] font-bold text-slate-900">
          Pedestre<br />Confianca: 92%
        </div>
        <div className="absolute bottom-3 left-3 rounded-md bg-slate-950/80 px-3 py-2 text-[11px] font-semibold text-white">
          Deteccoes: 15<br />FPS: 24.7
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Fonte:</span>
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-2 font-semibold text-slate-700">Upload de Video</span>
        </div>
        <div className="flex gap-2">
          <Button className="h-9 rounded-lg text-xs"><Upload className="h-4 w-4" />Carregar Video</Button>
          <Button variant="secondary" className="h-9 rounded-lg text-xs"><Play className="h-4 w-4" />Iniciar Analise</Button>
        </div>
      </div>
    </Card>
  );
}

function RootCausePanel() {
  return (
    <Card className="p-4">
      <p className="text-xs font-bold text-brand">2. Analise de Risco Operacional</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {["Ensolarado", "Pico da Manha", "Dia Util"].map((item) => (
          <span key={item} className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-semibold text-slate-600">
            {item}
          </span>
        ))}
        <span className="rounded-lg bg-violet-50 px-2 py-1 text-[11px] font-bold text-brand">Alterar Cenario</span>
      </div>
      <div className="mt-5 grid items-center gap-5 md:grid-cols-[0.85fr_1fr] xl:grid-cols-1 2xl:grid-cols-[0.85fr_1fr]">
        <div className="mx-auto flex h-40 w-40 items-center justify-center rounded-full bg-[conic-gradient(#ef4444_0_40%,#f97316_40%_65%,#f59e0b_65%_85%,#22c55e_85%_95%,#3b82f6_95%_100%)]">
          <div className="h-20 w-20 rounded-full bg-white" />
        </div>
        <div className="space-y-2">
          {violationData.map((item) => (
            <div key={item.name} className="flex items-center justify-between gap-3 text-xs">
              <span className="flex items-center gap-2 font-semibold text-slate-600">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.fill }} />
                {item.name}
              </span>
              <span className="font-bold text-slate-900">{item.value}%</span>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4 rounded-xl bg-violet-50 p-3">
        <p className="text-xs font-bold text-brand">Insight Principal:</p>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Excesso de velocidade e travessias em conflito sao os fatores mais provaveis neste cenario.
        </p>
      </div>
    </Card>
  );
}

function ManagementReportPanel() {
  return (
    <Card className="p-4">
      <p className="text-xs font-bold text-brand">3. Relatorio Gerencial (Impacto e Tendencias)</p>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <MiniMetric label="Total de infracoes" value="1.234" tone="text-brand" />
        <MiniMetric label="Taxa de reducao" value="8.7%" tone="text-danger" />
        <MiniMetric label="Confianca" value="96%" tone="text-success" />
      </div>
      <div className="mt-5">
        <p className="mb-2 text-xs font-bold text-slate-700">Infracoes por Horario</p>
        <div className="flex h-36 items-end gap-2 rounded-xl border border-slate-200 bg-white p-3">
          {flowData.map((item) => (
            <div key={item.hour} className="flex flex-1 flex-col items-center gap-2">
              <div className="w-full rounded-t-md bg-brand" style={{ height: `${Math.max(item.carros / 4, 20)}px` }} />
              <span className="text-[10px] font-semibold text-slate-400">{item.hour}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4">
        <p className="mb-2 text-xs font-bold text-slate-700">Mapa de Calor - Pontos Criticos</p>
        <div className="grid grid-cols-5 gap-1 rounded-xl border border-slate-200 bg-white p-3">
          {heatmapData.flatMap((row, rowIndex) =>
            row.map((value, columnIndex) => (
              <div
                key={`${rowIndex}-${columnIndex}`}
                className="aspect-square rounded-md"
                style={{ backgroundColor: `rgba(109, 40, 217, ${Math.max(value / 100, 0.18)})` }}
              />
            ))
          )}
        </div>
      </div>
    </Card>
  );
}

function MiniMetric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <p className="text-[10px] font-semibold text-slate-400">{label}</p>
      <p className={`mt-1 text-lg font-bold ${tone}`}>{value}</p>
    </div>
  );
}

function VideoPanel({ compact }: { compact: boolean }) {
  return (
    <Card className={compact ? "min-h-[430px]" : "min-h-[600px]"}>
      <div className="flex h-full min-h-[360px] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-white text-brand shadow-soft">
          <Camera className="h-8 w-8" aria-hidden="true" />
        </div>
        <h2 className="text-lg font-semibold text-slate-950">O video analisado aparecera aqui.</h2>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          Area preparada para receber upload local agora e streaming de cameras via API futuramente.
        </p>
        <Button className="mt-6">
          <Upload className="h-4 w-4" aria-hidden="true" />
          Carregar video
        </Button>
      </div>
    </Card>
  );
}

function AiSummary() {
  return (
    <Card className="space-y-5">
      <div>
        <CardTitle>Resumo da IA</CardTitle>
        <CardDescription>Leitura operacional do cruzamento monitorado</CardDescription>
      </div>
      <SummaryRow label="Principal causa" value="Excesso de velocidade" />
      <SummaryRow label="Nivel de risco" value="Alto" tone="text-danger" />
      <SummaryRow label="Ultima atualizacao" value="Ha 2 minutos" />
      <div className="rounded-2xl bg-violet-50 p-4 text-sm leading-6 text-slate-700">
        A IA recomenda reduzir o tempo de resposta semaforica e priorizar fiscalizacao automatizada no sentido oeste.
      </div>
    </Card>
  );
}

function SummaryRow({ label, value, tone = "text-slate-950" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-4">
      <span className="text-sm text-slate-500">{label}</span>
      <span className={`text-right text-sm font-semibold ${tone}`}>{value}</span>
    </div>
  );
}

function MonitoringPage() {
  return (
    <div className="space-y-6">
      <VideoPanel compact />
      <div className="flex flex-wrap gap-3">
        <Button>
          <Upload className="h-4 w-4" aria-hidden="true" />
          Upload
        </Button>
        <Button variant="secondary">
          <Play className="h-4 w-4" aria-hidden="true" />
          Iniciar Analise
        </Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {monitoringStats.map((stat) => (
          <Card key={stat.label}>
            <p className="text-sm font-medium text-slate-500">{stat.label}</p>
            <p className="mt-3 text-3xl font-semibold text-slate-950">{stat.value}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

function DiagnosisPage() {
  const { register, handleSubmit } = useForm<ScenarioForm>({
    defaultValues: { cidade: "Sao Paulo", clima: "Chuva leve", horario: "18:00", fluxo: "Alto", dia: "Sexta-feira" }
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiagnosisResult | null>(null);

  function submit() {
    setLoading(true);
    setResult(null);
    window.setTimeout(() => {
      setResult({
        risk: "72%",
        cause: "Excesso de velocidade em horario de pico",
        confidence: "94%",
        recommendations: [
          "Ativar semaforo inteligente nos acessos laterais.",
          "Reduzir limite operacional para 40 km/h.",
          "Ampliar sinalizacao luminosa para pedestres."
        ]
      });
      setLoading(false);
    }, 2000);
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <Card>
        <CardTitle>Analisar cenario</CardTitle>
        <CardDescription>Simulacao local preparada para futura chamada REST.</CardDescription>
        <form onSubmit={handleSubmit(submit)} className="mt-6 grid gap-4">
          <Field label="Cidade">
            <Input {...register("cidade")} />
          </Field>
          <Field label="Clima">
            <SelectField {...register("clima")}>
              <option>Chuva leve</option>
              <option>Tempo limpo</option>
              <option>Neblina</option>
              <option>Chuva forte</option>
            </SelectField>
          </Field>
          <Field label="Horario">
            <Input type="time" {...register("horario")} />
          </Field>
          <Field label="Fluxo de veiculos">
            <SelectField {...register("fluxo")}>
              <option>Baixo</option>
              <option>Medio</option>
              <option>Alto</option>
              <option>Critico</option>
            </SelectField>
          </Field>
          <Field label="Dia da semana">
            <SelectField {...register("dia")}>
              <option>Segunda-feira</option>
              <option>Terca-feira</option>
              <option>Quarta-feira</option>
              <option>Quinta-feira</option>
              <option>Sexta-feira</option>
              <option>Sabado</option>
              <option>Domingo</option>
            </SelectField>
          </Field>
          <Button type="submit" disabled={loading}>
            {loading ? <Spinner className="h-4 w-4 text-white" /> : <Zap className="h-4 w-4" />}
            Analisar Cenario
          </Button>
        </form>
      </Card>
      <Card className="min-h-[560px]">
        {loading && <LoadingState text="A IA esta analisando o cenario..." />}
        {!loading && !result && (
          <EmptyResult text="Preencha os parametros e execute a analise para visualizar a leitura operacional." />
        )}
        {!loading && result && <DiagnosisResultView result={result} />}
      </Card>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-2 text-sm font-semibold text-slate-700">
      {label}
      {children}
    </label>
  );
}

function LoadingState({ text }: { text: string }) {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center gap-4 text-center">
      <Spinner className="h-10 w-10" />
      <p className="text-sm font-semibold text-slate-600">{text}</p>
    </div>
  );
}

function EmptyResult({ text }: { text: string }) {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center rounded-2xl bg-slate-50 p-8 text-center">
      <ShieldAlert className="h-10 w-10 text-slate-300" aria-hidden="true" />
      <p className="mt-4 max-w-sm text-sm text-slate-500">{text}</p>
    </div>
  );
}

function DiagnosisResultView({ result }: { result: DiagnosisResult }) {
  return (
    <div className="space-y-5">
      <UrbanCameraFeed className="h-56 w-full rounded-2xl" />
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric label="Risco de acidentes" value={result.risk} tone="text-danger" />
        <Metric label="Principal causa" value={result.cause} />
        <Metric label="Confianca" value={result.confidence} tone="text-brand" />
      </div>
      <div className="rounded-2xl bg-slate-50 p-5">
        <h3 className="font-semibold text-slate-950">Recomendacoes</h3>
        <ul className="mt-3 space-y-2 text-sm text-slate-600">
          {result.recommendations.map((item) => (
            <li key={item} className="flex gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none text-success" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Metric({ label, value, tone = "text-slate-950" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase text-slate-400">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function ReportsPage() {
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <PieChartCard />
      <BarChartCard />
      <LineChartCard />
      <HeatmapCard />
    </div>
  );
}

function ScenariosPage() {
  const [selectedCity, setSelectedCity] = useState(cityScenarios[0]);
  const scenarioData = useMemo(
    () =>
      flowData.map((item, index) => ({
        ...item,
        carros: Math.round(item.carros * (selectedCity.trafficIndex / 80) + index * 8),
        pedestres: Math.round(item.pedestres * (selectedCity.risk / 70))
      })),
    [selectedCity]
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cityScenarios.map((scenario) => (
          <button key={scenario.city} onClick={() => setSelectedCity(scenario)} className="text-left">
            <Card className={selectedCity.city === scenario.city ? "border-brand ring-4 ring-brand/10" : ""}>
              <div className="flex items-center gap-2 text-sm font-semibold text-brand">
                <MapPin className="h-4 w-4" aria-hidden="true" />
                {scenario.city}
              </div>
              <p className="mt-4 text-3xl font-semibold text-slate-950">{scenario.risk}%</p>
              <p className="mt-1 text-sm text-slate-500">{scenario.mainCause}</p>
            </Card>
          </button>
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-[1fr_0.8fr]">
        <BarChartCard data={scenarioData} />
        <Card>
          <CardTitle>Dados atualizados</CardTitle>
          <div className="mt-5 space-y-4">
            <SummaryRow label="Cidade" value={selectedCity.city} />
            <SummaryRow label="Indice de trafego" value={`${selectedCity.trafficIndex}%`} />
            <SummaryRow label="Confianca" value={`${selectedCity.confidence}%`} />
            <SummaryRow label="Fluxo de veiculos" value={`${selectedCity.vehicleFlow}/h`} />
          </div>
        </Card>
      </div>
    </div>
  );
}

function OperationsCenterPage() {
  const [selectedPoint, setSelectedPoint] = useState<OperationPoint>(operationPoints[0]);

  return (
    <div className="space-y-6">
      <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <Card className="overflow-hidden p-0">
          <div className="border-b border-slate-200 p-5">
            <p className="text-sm font-bold text-brand">Central Inteligente de Monitoramento de Transito</p>
            <p className="mt-1 text-sm text-slate-500">Mapa operacional com pontos criticos e indicadores simulados de risco.</p>
          </div>
          <div className="relative min-h-[560px] overflow-hidden bg-slate-100">
            <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(100,116,139,0.16)_1px,transparent_1px),linear-gradient(0deg,rgba(100,116,139,0.16)_1px,transparent_1px)] bg-[size:52px_52px]" />
            <div className="absolute left-[8%] top-[18%] h-[68%] w-10 -rotate-12 rounded-full bg-white shadow-sm" />
            <div className="absolute left-[22%] top-[8%] h-[86%] w-12 rotate-[28deg] rounded-full bg-white shadow-sm" />
            <div className="absolute left-[4%] right-[8%] top-[42%] h-14 rounded-full bg-white shadow-sm" />
            <div className="absolute bottom-[18%] left-[18%] right-[12%] h-12 -rotate-6 rounded-full bg-white shadow-sm" />

            <div className="absolute left-[12%] top-[12%] grid grid-cols-4 gap-3 opacity-80">
              {Array.from({ length: 28 }).map((_, index) => (
                <div key={index} className="h-12 w-16 rounded-lg bg-white shadow-sm" />
              ))}
            </div>
            <div className="absolute bottom-12 right-14 h-36 w-48 rounded-[2rem] bg-emerald-100" />
            <div className="absolute bottom-20 right-24 h-20 w-24 rounded-full bg-emerald-200" />

            {operationPoints.map((point) => (
              <button
                key={point.id}
                onClick={() => setSelectedPoint(point)}
                aria-label={`Selecionar ${point.name}`}
                className="absolute -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${point.position.x}%`, top: `${point.position.y}%` }}
              >
                <motion.span
                  className={`flex h-12 w-12 items-center justify-center rounded-2xl border-4 border-white shadow-soft ${riskBackground(point.risk)}`}
                  animate={{ scale: selectedPoint.id === point.id ? [1, 1.08, 1] : 1 }}
                  transition={{ duration: 1.4, repeat: selectedPoint.id === point.id ? Infinity : 0 }}
                >
                  {point.id === "school-zone" && <School className="h-5 w-5 text-white" />}
                  {point.id === "hospital" && <Hospital className="h-5 w-5 text-white" />}
                  {point.id === "main-avenue" && <Car className="h-5 w-5 text-white" />}
                  {point.id === "central-crossing" && <TrafficCone className="h-5 w-5 text-white" />}
                </motion.span>
                <span className="mt-2 hidden rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-700 shadow-sm md:block">
                  {point.name}
                </span>
              </button>
            ))}
          </div>
        </Card>

        <OperationDetails point={selectedPoint} />
      </div>
    </div>
  );
}

function riskBackground(risk: OperationPoint["risk"]) {
  if (risk === "green") return "bg-success";
  if (risk === "yellow") return "bg-warning";
  return "bg-danger";
}

function riskLabel(risk: OperationPoint["risk"]) {
  if (risk === "green") return "Baixo";
  if (risk === "yellow") return "Moderado";
  return "Critico";
}

function OperationDetails({ point }: { point: OperationPoint }) {
  return (
    <motion.aside
      key={point.id}
      initial={{ opacity: 0, x: 18 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.24 }}
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">{point.type}</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">{point.name}</h2>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-bold text-white ${riskBackground(point.risk)}`}>
          Risco {riskLabel(point.risk)}
        </span>
      </div>
      <CityPointIllustration point={point} />
      <div className="mt-5 grid grid-cols-2 gap-3">
        <Metric label="Veiculos" value={String(point.vehicles)} />
        <Metric label="Pedestres" value={String(point.pedestrians)} />
        <Metric label="Maior movimento" value={point.peakHour} />
        <Metric label="Infracoes" value={String(point.violations)} tone="text-danger" />
      </div>
      <div className="mt-5 rounded-2xl bg-slate-50 p-4">
        <p className="text-xs font-bold uppercase text-slate-400">Principal causa provavel</p>
        <p className="mt-2 text-sm font-semibold leading-6 text-slate-800">{point.likelyCause}</p>
      </div>
      <div className="mt-4 flex items-center justify-between rounded-2xl bg-violet-50 p-4">
        <span className="text-sm font-bold text-brand">Confianca da IA</span>
        <span className="text-2xl font-extrabold text-brand">{point.confidence}%</span>
      </div>
      <Button className="mt-5 w-full">
        <Camera className="h-4 w-4" />
        Visualizar Monitoramento
      </Button>
    </motion.aside>
  );
}

function SmartCityChallenge({
  selectedInvestments,
  spent,
  budget,
  planApplied,
  riskBefore,
  riskAfter,
  onToggle,
  onApply,
  onReset
}: {
  selectedInvestments: string[];
  spent: number;
  budget: number;
  planApplied: boolean;
  riskBefore: number;
  riskAfter: number;
  onToggle: (id: string) => void;
  onApply: () => void;
  onReset: () => void;
}) {
  return (
    <Card>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-bold text-brand">Planeje sua Smart City</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Escolha melhorias para reduzir acidentes</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Use um orcamento ficticio e veja como cada decisao muda o indice de risco urbano com dados simulados.
          </p>
        </div>
        <div className="flex gap-3">
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs font-bold text-slate-400">Orcamento</p>
            <p className="text-xl font-extrabold text-slate-950">R$ {budget} mi</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs font-bold text-slate-400">Usado</p>
            <p className={spent > budget ? "text-xl font-extrabold text-danger" : "text-xl font-extrabold text-brand"}>
              R$ {spent} mi
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-5 xl:grid-cols-[1fr_0.72fr]">
        <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
          {smartCityInvestments.map((investment) => {
            const selected = selectedInvestments.includes(investment.id);
            return (
              <button
                key={investment.id}
                onClick={() => onToggle(investment.id)}
                className={`rounded-2xl border p-4 text-left transition ${
                  selected ? "border-brand bg-violet-50 ring-4 ring-brand/10" : "border-slate-200 bg-white hover:border-brand/50"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-bold text-slate-950">{investment.label}</p>
                    <p className="mt-2 text-xs leading-5 text-slate-500">{investment.description}</p>
                  </div>
                  {selected ? <CheckCircle2 className="h-5 w-5 text-brand" /> : <DollarSign className="h-5 w-5 text-slate-300" />}
                </div>
                <div className="mt-4 flex items-center justify-between text-xs font-bold">
                  <span className="text-slate-500">R$ {investment.cost} milhoes</span>
                  <span className="text-success">-{investment.impact}% risco</span>
                </div>
              </button>
            );
          })}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-white p-4">
              <p className="text-xs font-bold text-slate-400">Antes</p>
              <p className="mt-2 text-sm text-slate-500">Indice de risco</p>
              <p className="text-4xl font-extrabold text-danger">{riskBefore}%</p>
              <p className="mt-1 text-xs font-bold text-danger">Base operacional</p>
            </div>
            <div className="rounded-2xl bg-white p-4">
              <p className="text-xs font-bold text-slate-400">Depois</p>
              <p className="mt-2 text-sm text-slate-500">Novo risco</p>
              <p className="text-4xl font-extrabold text-success">{planApplied ? `${riskAfter}%` : "--"}</p>
              <p className="mt-1 text-xs font-bold text-success">{planApplied ? `Reducao de ${riskBefore - riskAfter}%` : "Aguardando plano"}</p>
            </div>
          </div>

          <div className="mt-4 rounded-2xl bg-white p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-700">
              <Wallet className="h-4 w-4 text-brand" />
              Resultado estimado
            </div>
            {planApplied ? (
              <p className="text-sm leading-6 text-slate-600">
                O plano reduziu o risco estimado de {riskBefore}% para {riskAfter}%, uma queda de {riskBefore - riskAfter}%.
                As escolhas combinam fiscalizacao inteligente, prioridade semaforica, melhor visibilidade e educacao viaria.
              </p>
            ) : (
              <p className="text-sm leading-6 text-slate-500">
                Selecione melhorias e aplique o plano para recalcular a seguranca geral da cidade.
              </p>
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <Button onClick={onApply} disabled={selectedInvestments.length === 0}>
              <Zap className="h-4 w-4" />
              Aplicar Plano
            </Button>
            <Button variant="ghost" onClick={onReset}>
              <X className="h-4 w-4" />
              Limpar escolhas
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

function InteractivePage() {
  const [phase, setPhase] = useState<"idle" | "analyzing" | "result" | "recalculating" | "complete">("idle");
  const [improvements, setImprovements] = useState<string[]>([]);
  const [selectedInvestments, setSelectedInvestments] = useState<string[]>([]);
  const [planApplied, setPlanApplied] = useState(false);
  const [activeExperience, setActiveExperience] = useState<"simulation" | "planner">("simulation");

  function analyze() {
    setPhase("analyzing");
    window.setTimeout(() => setPhase("result"), 2000);
  }

  function recalculate() {
    setPhase("recalculating");
    window.setTimeout(() => setPhase("complete"), 2000);
  }

  function toggleImprovement(value: string) {
    setImprovements((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
    );
  }

  const resultVisible = phase === "result" || phase === "recalculating" || phase === "complete";
  const complete = phase === "complete";
  const selectedPlan = smartCityInvestments.filter((item) => selectedInvestments.includes(item.id));
  const spent = selectedPlan.reduce((total, item) => total + item.cost, 0);
  const impact = selectedPlan.reduce((total, item) => total + item.impact, 0);
  const budget = 80;
  const riskBefore = 68;
  const riskAfter = Math.max(22, riskBefore - impact);

  function toggleInvestment(id: string) {
    const item = smartCityInvestments.find((investment) => investment.id === id);
    if (!item) return;

    setPlanApplied(false);
    setSelectedInvestments((current) => {
      if (current.includes(id)) {
        return current.filter((selected) => selected !== id);
      }

      const currentSpent = smartCityInvestments
        .filter((investment) => current.includes(investment.id))
        .reduce((total, investment) => total + investment.cost, 0);

      if (currentSpent + item.cost > budget) {
        return current;
      }

      return [...current, id];
    });
  }

  return (
    <div className="space-y-5">
      <div className="text-center">
        <h2 className="text-3xl font-extrabold tracking-tight text-slate-950">Experiencia Interativa - CogniMove</h2>
        <p className="mt-1 text-sm font-medium text-slate-500">Voce toma decisoes e a IA mostra o impacto em tempo real.</p>
      </div>

      <div className="mx-auto grid max-w-xl rounded-2xl border border-slate-200 bg-white p-1 shadow-panel sm:grid-cols-2">
        {[
          { id: "simulation", label: "Simulacao guiada" },
          { id: "planner", label: "Planeje sua Smart City" }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveExperience(tab.id as "simulation" | "planner")}
            className={`rounded-xl px-4 py-3 text-sm font-bold transition ${
              activeExperience === tab.id ? "bg-brand text-white shadow-soft" : "text-slate-500 hover:text-slate-950"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeExperience === "planner" && (
        <SmartCityChallenge
          selectedInvestments={selectedInvestments}
          spent={spent}
          budget={budget}
          planApplied={planApplied}
          riskBefore={riskBefore}
          riskAfter={riskAfter}
          onToggle={toggleInvestment}
          onApply={() => setPlanApplied(true)}
          onReset={() => {
            setSelectedInvestments([]);
            setPlanApplied(false);
          }}
        />
      )}

      {activeExperience === "simulation" && (
        <>
      <div className="grid gap-4 xl:grid-cols-[1fr_36px_1fr_36px_1fr]">
        <FlowCard number="1" title="Escolha o cenario" subtitle="Defina as condicoes do transito para analise.">
          <div className="rounded-xl border border-slate-200 p-4">
            <p className="mb-3 text-center text-xs font-bold text-slate-700">Simule um cenario de transito</p>
            <div className="space-y-3">
              <CompactField label="Cidade"><SelectField><option>Rio de Janeiro</option><option>Sao Paulo</option><option>Curitiba</option></SelectField></CompactField>
              <CompactField label="Clima">
                <div className="grid grid-cols-2 gap-2">
                  <Button variant="secondary" className="h-9 text-xs"><CloudSun className="h-4 w-4" />Sol</Button>
                  <Button variant="ghost" className="h-9 border border-slate-200 text-xs">Chuva</Button>
                </div>
              </CompactField>
              <CompactField label="Horario">
                <div className="grid grid-cols-3 gap-2">
                  {["Manha", "Tarde", "Noite"].map((item) => <span key={item} className="rounded-lg border border-slate-200 bg-violet-50 px-2 py-2 text-center text-xs font-bold text-brand">{item}</span>)}
                </div>
              </CompactField>
              <CompactField label="Fluxo de veiculos">
                <input type="range" min="0" max="100" defaultValue="70" className="w-full accent-brand" />
              </CompactField>
              <Button className="w-full" onClick={analyze}><Zap className="h-4 w-4" />Analisar Cenario</Button>
            </div>
          </div>
        </FlowCard>
        <FlowArrow />
        <FlowCard number="2" title="Analise em andamento" subtitle="A IA esta processando os dados do cenario escolhido.">
          <RoadLoading active={phase === "analyzing"} label={phase === "analyzing" ? "Analisando cenario..." : "Aguardando analise"} />
        </FlowCard>
        <FlowArrow />
        <FlowCard number="3" title="Veja os resultados da analise" subtitle="A IA identifica os principais riscos e fatores do cenario.">
          <div className="grid gap-3 md:grid-cols-[0.75fr_1.25fr]">
            <div className="space-y-3">
              <ResultBox label="Risco de acidentes" value={resultVisible ? "72%" : "--"} tone="text-danger" icon={<TrendingDown className="h-5 w-5" />} />
              <ResultBox label="Principal fator" value={resultVisible ? "Excesso de velocidade" : "--"} tone="text-slate-900" icon={<Radar className="h-5 w-5" />} />
              <ResultBox label="Confianca da IA" value={resultVisible ? "94%" : "--"} tone="text-success" icon={<ShieldCheck className="h-5 w-5" />} />
            </div>
            <div>
              <p className="mb-2 text-xs font-bold text-slate-700">Visualizacao da IA</p>
              <div className="relative h-52 overflow-hidden rounded-xl">
                <UrbanCameraFeed className="h-full w-full" />
                <span className="absolute bottom-5 left-8 h-16 w-16 border-2 border-red-500" />
                <span className="absolute bottom-8 right-10 h-14 w-10 border-2 border-amber-400" />
                <span className="absolute right-16 top-8 h-12 w-8 border-2 border-emerald-500" />
              </div>
              <div className="mt-2 flex justify-center gap-3 text-[10px] font-semibold text-slate-500">
                <span className="text-red-500">Carro</span><span className="text-amber-500">Pedestre</span><span className="text-emerald-600">Semaforo</span>
              </div>
            </div>
          </div>
        </FlowCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_36px_1fr_36px_1fr]">
        <FlowCard number="4" title="Escolha intervencoes" subtitle="Selecione as acoes que deseja aplicar no cenario.">
          <div className="rounded-xl border border-slate-200 p-4">
            <p className="mb-4 text-xs font-bold text-slate-700">Qual intervencao voce faria?</p>
            <div className="space-y-3">
              {[
                ["Radar", <Radar key="radar" className="h-4 w-4" />],
                ["Ajustar tempo do semaforo", <TrafficCone key="traffic" className="h-4 w-4" />],
                ["Nova faixa de pedestres", <Footprints key="foot" className="h-4 w-4" />],
                ["Melhorar iluminacao", <Lightbulb key="light" className="h-4 w-4" />]
              ].map(([item, icon]) => (
                <label key={String(item)} className="flex cursor-pointer items-center justify-between gap-3 text-xs font-semibold text-slate-700">
                  <span className="flex items-center gap-2">
                    <input type="checkbox" checked={improvements.includes(String(item))} onChange={() => toggleImprovement(String(item))} className="h-4 w-4 accent-brand" />
                    {item}
                  </span>
                  {icon}
                </label>
              ))}
            </div>
            <Button className="mt-5 w-full" onClick={recalculate} disabled={improvements.length === 0}><Zap className="h-4 w-4" />Aplicar melhorias</Button>
          </div>
        </FlowCard>
        <FlowArrow />
        <FlowCard number="5" title="Recalculando cenario" subtitle="A IA esta avaliando o impacto das intervencoes escolhidas.">
          <RoadLoading active={phase === "recalculating"} label={phase === "recalculating" ? "Recalculando cenario..." : "Aguardando melhorias"} />
        </FlowCard>
        <FlowArrow />
        <FlowCard number="6" title="Compare os resultados" subtitle="Veja como suas decisoes impactaram a seguranca no transito.">
          <div className="grid gap-3 md:grid-cols-[1fr_32px_1fr]">
            <Card className="p-4 shadow-none">
              <p className="text-xs font-bold text-slate-600">Antes</p>
              <p className="mt-3 text-xs text-slate-500">Risco de acidentes</p>
              <p className="text-4xl font-extrabold text-danger">72%</p>
              <p className="text-xs font-bold text-danger">Risco Alto</p>
            </Card>
            <div className="hidden items-center justify-center md:flex">
              <ArrowRight className="h-6 w-6 text-slate-400" />
            </div>
            <Card className="bg-emerald-50 p-4 shadow-none">
              <p className="text-xs font-bold text-success">Depois</p>
              <p className="mt-3 text-xs text-slate-500">Novo risco de acidentes</p>
              <p className="text-4xl font-extrabold text-success">{complete ? "43%" : "--"}</p>
              <p className="text-xs font-bold text-success">{complete ? "Reducao de 29%" : "Aguardando"}</p>
            </Card>
          </div>
          <div className="mt-4 rounded-xl bg-emerald-50 p-4 text-xs font-semibold leading-5 text-emerald-700">
            A combinacao de radar, ajuste semaforico e melhor iluminacao reduziu significativamente o risco neste cenario.
          </div>
          <Button className="mt-4 w-full" variant="ghost" onClick={() => { setPhase("idle"); setImprovements([]); }}>
            <RotateCcw className="h-4 w-4" />Reiniciar simulacao
          </Button>
        </FlowCard>
      </div>
        </>
      )}
    </div>
  );
}

function FlowCard({ number, title, subtitle, children }: { number: string; title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Card className="h-full p-4">
        <div className="mb-4 flex gap-3">
          <span className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-brand text-sm font-bold text-white shadow-soft">{number}</span>
          <div>
            <h3 className="text-sm font-extrabold text-slate-950">{title}</h3>
            <p className="text-xs font-medium text-slate-500">{subtitle}</p>
          </div>
        </div>
        {children}
      </Card>
    </motion.div>
  );
}

function FlowArrow() {
  return (
    <div className="hidden items-center justify-center xl:flex">
      <ArrowRight className="h-7 w-7 text-brand" />
    </div>
  );
}

function CompactField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[92px_1fr] items-center gap-3">
      <span className="text-xs font-bold text-slate-600">{label}</span>
      {children}
    </div>
  );
}

function RoadLoading({ active, label }: { active: boolean; label: string }) {
  return (
    <div className="relative flex min-h-72 flex-col items-center justify-center overflow-hidden rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-100">
      {active ? <Spinner className="h-14 w-14" /> : <Car className="h-14 w-14 text-slate-300" />}
      <p className="mt-5 text-sm font-bold text-slate-800">{label}</p>
      <p className="mt-3 text-xs text-slate-400">Isso pode levar alguns segundos</p>
      <div className="absolute bottom-0 h-20 w-full bg-gradient-to-t from-slate-200 to-transparent" />
    </div>
  );
}

function ResultBox({ label, value, tone, icon }: { label: string; value: string; tone: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-bold text-slate-600">{label}</p>
        <span className="text-slate-500">{icon}</span>
      </div>
      <p className={`mt-2 text-3xl font-extrabold ${tone}`}>{value}</p>
    </div>
  );
}

function AboutPage() {
  return (
    <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
      <Card>
        <CardTitle>Objetivo</CardTitle>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          O CogniMove demonstra como inteligencia artificial pode apoiar decisoes de mobilidade urbana,
          identificando riscos, padroes de fluxo e recomendacoes para reduzir acidentes em tempo real.
        </p>
      </Card>
      <Card>
        <CardTitle>FECART</CardTitle>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          Projeto preparado para apresentacao com foco em clareza visual, dados simulados e experiencia interativa.
        </p>
      </Card>
      <Card>
        <CardTitle>Tecnologias</CardTitle>
        <div className="mt-4 flex flex-wrap gap-2">
          {["Next.js 15", "React 19", "TypeScript", "Tailwind CSS", "shadcn/ui", "Framer Motion", "Recharts", "React Hook Form"].map((tech) => (
            <span key={tech} className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">{tech}</span>
          ))}
        </div>
      </Card>
      <Card>
        <CardTitle>Equipe e orientador</CardTitle>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          Espaco reservado para nomes da equipe, turma, instituicao e orientador responsavel pelo projeto.
        </p>
      </Card>
    </div>
  );
}

function SettingsPage() {
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <Card>
        <CardTitle>Preferencias do sistema</CardTitle>
        <div className="mt-5 space-y-4">
          <Field label="Modelo de IA"><SelectField><option>CogniVision Mock v1</option><option>API REST futura</option></SelectField></Field>
          <Field label="Intervalo de atualizacao"><SelectField><option>Tempo real</option><option>A cada 5 minutos</option><option>A cada 15 minutos</option></SelectField></Field>
        </div>
      </Card>
      <Card>
        <CardTitle>Integracao futura</CardTitle>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          Os dados atuais sao mockados, mas a estrutura isola o dominio em `mock/traffic-data.ts`.
          A proxima etapa natural e substituir essa origem por services REST mantendo os componentes intactos.
        </p>
      </Card>
    </div>
  );
}
